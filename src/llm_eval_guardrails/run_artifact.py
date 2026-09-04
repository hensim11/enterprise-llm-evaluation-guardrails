"""Versioned, machine-readable artefacts for raw system execution runs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import NoReturn, TypeAlias

from llm_eval_guardrails.evaluation_case import EvaluationCase

RUN_ARTIFACT_SCHEMA_VERSION = "1"
SUPPORTED_RUN_ARTIFACT_SCHEMA_VERSIONS = frozenset({RUN_ARTIFACT_SCHEMA_VERSION})

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ExecutionStatus(StrEnum):
    """Raw execution states; these are not evaluation outcomes."""

    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ExecutionError:
    """Serializable details for one ordinary system execution exception."""

    type: str
    message: str

    def __post_init__(self) -> None:
        _non_empty_string(self.type, "error.type")
        _string(self.message, "error.message")

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return the documented error shape."""
        return {"type": self.type, "message": self.message}

    @classmethod
    def from_mapping(cls, value: object) -> ExecutionError:
        """Validate and construct error details from their serialized shape."""
        mapping = _mapping(value, "error")
        _require_exact_fields(mapping, {"type", "message"}, "error")
        return cls(
            type=_non_empty_string(mapping["type"], "error.type"),
            message=_string(mapping["message"], "error.message"),
        )


@dataclass(frozen=True, slots=True)
class CaseExecutionResult:
    """Raw execution evidence for exactly one evaluation case."""

    case_id: str
    status: ExecutionStatus
    output: str | None
    duration_seconds: float
    error: ExecutionError | None

    def __post_init__(self) -> None:
        _non_empty_string(self.case_id, "case_id")
        if not isinstance(self.status, ExecutionStatus):
            raise TypeError("status must be an ExecutionStatus")
        _duration(self.duration_seconds)

        if self.status is ExecutionStatus.SUCCESS:
            if not isinstance(self.output, str):
                raise ValueError("successful result output must be a string")
            if self.error is not None:
                raise ValueError("successful result error must be None")
        else:
            if self.output is not None:
                raise ValueError("error result output must be None")
            if not isinstance(self.error, ExecutionError):
                raise ValueError("error result must include ExecutionError details")

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return the documented case-result shape with explicit nulls."""
        return {
            "case_id": self.case_id,
            "status": self.status.value,
            "output": self.output,
            "duration_seconds": self.duration_seconds,
            "error": None if self.error is None else self.error.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, value: object) -> CaseExecutionResult:
        """Validate and construct a case result from its serialized shape."""
        mapping = _mapping(value, "results[]")
        _require_exact_fields(
            mapping,
            {"case_id", "status", "output", "duration_seconds", "error"},
            "results[]",
        )
        status_text = _non_empty_string(mapping["status"], "results[].status")
        try:
            status = ExecutionStatus(status_text)
        except ValueError as error:
            raise ValueError("results[].status must be 'success' or 'error'") from error

        raw_error = mapping["error"]
        execution_error = None if raw_error is None else ExecutionError.from_mapping(raw_error)
        return cls(
            case_id=_non_empty_string(mapping["case_id"], "results[].case_id"),
            status=status,
            output=mapping["output"],  # validated by the constructor
            duration_seconds=_duration(mapping["duration_seconds"]),
            error=execution_error,
        )


@dataclass(frozen=True, slots=True)
class SystemProvenance:
    """System identity and explicitly allowlisted, non-secret configuration."""

    id: str
    configuration: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _non_empty_string(self.id, "system.id")
        object.__setattr__(
            self,
            "configuration",
            _json_object(self.configuration, "system.configuration"),
        )

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return a defensive serialized copy of system provenance."""
        return {
            "id": self.id,
            "configuration": _json_object(self.configuration, "system.configuration"),
        }

    @classmethod
    def from_mapping(cls, value: object) -> SystemProvenance:
        """Validate and construct system provenance from its serialized shape."""
        mapping = _mapping(value, "system")
        _require_exact_fields(mapping, {"id", "configuration"}, "system")
        return cls(
            id=_non_empty_string(mapping["id"], "system.id"),
            configuration=_json_object(mapping["configuration"], "system.configuration"),
        )


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    """Source plus an ordered, validated case snapshot and its fingerprint."""

    source: str
    cases: tuple[EvaluationCase, ...]

    def __post_init__(self) -> None:
        _non_empty_string(self.source, "dataset.source")
        if not isinstance(self.cases, tuple) or not self.cases:
            raise ValueError("dataset.cases must be a non-empty tuple")
        copied_cases: list[EvaluationCase] = []
        first_id_index: dict[str, int] = {}
        for index, case in enumerate(self.cases):
            if not isinstance(case, EvaluationCase):
                raise TypeError(f"dataset.cases[{index}] must be an EvaluationCase")
            if case.id in first_id_index:
                raise ValueError(
                    f"dataset.cases[{index}].id duplicates "
                    f"dataset.cases[{first_id_index[case.id]}].id value {case.id!r}"
                )
            first_id_index[case.id] = index
            copied_cases.append(EvaluationCase.from_mapping(case.to_mapping()))
        object.__setattr__(self, "cases", tuple(copied_cases))

    @property
    def fingerprint(self) -> str:
        """SHA-256 of the canonical JSON encoding of the ordered case snapshot."""
        return _case_fingerprint(self.cases)

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return dataset provenance with its current, matching fingerprint."""
        cases = [case.to_mapping() for case in self.cases]
        return {
            "source": self.source,
            "fingerprint": {"algorithm": "sha256", "value": _fingerprint(cases)},
            "cases": cases,
        }

    @classmethod
    def from_mapping(cls, value: object) -> DatasetProvenance:
        """Validate the case snapshot and verify its declared fingerprint."""
        mapping = _mapping(value, "dataset")
        _require_exact_fields(mapping, {"source", "fingerprint", "cases"}, "dataset")

        fingerprint = _mapping(mapping["fingerprint"], "dataset.fingerprint")
        _require_exact_fields(fingerprint, {"algorithm", "value"}, "dataset.fingerprint")
        if fingerprint["algorithm"] != "sha256":
            raise ValueError("dataset.fingerprint.algorithm must be 'sha256'")
        declared_fingerprint = _non_empty_string(fingerprint["value"], "dataset.fingerprint.value")

        raw_cases = mapping["cases"]
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError("dataset.cases must be a non-empty array")
        cases = tuple(EvaluationCase.from_mapping(case) for case in raw_cases)
        provenance = cls(
            source=_non_empty_string(mapping["source"], "dataset.source"),
            cases=cases,
        )
        if declared_fingerprint != provenance.fingerprint:
            raise ValueError("dataset fingerprint does not match the ordered case snapshot")
        return provenance


@dataclass(frozen=True, slots=True)
class RunArtifact:
    """One complete raw execution run, separate from future evaluation results."""

    run_id: str
    started_at: datetime
    system: SystemProvenance
    dataset: DatasetProvenance
    results: tuple[CaseExecutionResult, ...]
    schema_version: str = RUN_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _supported_schema_version(self.schema_version)
        _non_empty_string(self.run_id, "run_id")
        if not isinstance(self.started_at, datetime):
            raise TypeError("started_at must be a datetime")
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("started_at must include a timezone")
        object.__setattr__(self, "started_at", self.started_at.astimezone(UTC))
        if not isinstance(self.system, SystemProvenance):
            raise TypeError("system must be SystemProvenance")
        if not isinstance(self.dataset, DatasetProvenance):
            raise TypeError("dataset must be DatasetProvenance")
        if not isinstance(self.results, tuple):
            raise TypeError("results must be a tuple")
        if any(not isinstance(result, CaseExecutionResult) for result in self.results):
            raise TypeError("results must contain only CaseExecutionResult values")

        case_ids = tuple(case.id for case in self.dataset.cases)
        result_ids = tuple(result.case_id for result in self.results)
        if result_ids != case_ids:
            raise ValueError(
                "results must contain exactly one ordered result for every dataset case"
            )

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return the documented versioned JSON shape."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "started_at": _format_timestamp(self.started_at),
            "system": self.system.to_mapping(),
            "dataset": self.dataset.to_mapping(),
            "results": [result.to_mapping() for result in self.results],
        }

    @classmethod
    def from_mapping(cls, value: object) -> RunArtifact:
        """Validate and construct an artefact from its serialized shape."""
        mapping = _mapping(value, "$")
        _require_exact_fields(
            mapping,
            {"schema_version", "run_id", "started_at", "system", "dataset", "results"},
            "$",
        )
        schema_version = _non_empty_string(mapping["schema_version"], "schema_version")
        _supported_schema_version(schema_version)
        raw_results = mapping["results"]
        if not isinstance(raw_results, list):
            raise ValueError("results must be an array")
        return cls(
            schema_version=schema_version,
            run_id=_non_empty_string(mapping["run_id"], "run_id"),
            started_at=_parse_timestamp(mapping["started_at"]),
            system=SystemProvenance.from_mapping(mapping["system"]),
            dataset=DatasetProvenance.from_mapping(mapping["dataset"]),
            results=tuple(CaseExecutionResult.from_mapping(result) for result in raw_results),
        )


def write_run_artifact(artifact: RunArtifact, path: str | Path) -> None:
    """Write a new UTF-8 JSON artefact; serialization and I/O failures propagate."""
    if not isinstance(artifact, RunArtifact):
        raise TypeError("artifact must be a RunArtifact")
    serialized = json.dumps(
        artifact.to_mapping(),
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
    )
    with Path(path).open("x", encoding="utf-8", newline="\n") as artifact_file:
        artifact_file.write(serialized)
        artifact_file.write("\n")


def load_run_artifact(path: str | Path) -> RunArtifact:
    """Read and fully validate one UTF-8 JSON run artefact."""
    with Path(path).open("r", encoding="utf-8") as artifact_file:
        value = json.load(
            artifact_file,
            object_pairs_hook=_object_from_unique_pairs,
            parse_constant=_reject_non_standard_number,
        )
    return RunArtifact.from_mapping(value)


def _case_fingerprint(cases: tuple[EvaluationCase, ...]) -> str:
    return _fingerprint([case.to_mapping() for case in cases])


def _fingerprint(cases: list[dict[str, JsonValue]]) -> str:
    canonical = json.dumps(
        cases,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    text = _non_empty_string(value, "started_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("started_at must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("started_at must include a timezone")
    return parsed


def _duration(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("duration_seconds must be a number")
    duration = float(value)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("duration_seconds must be finite and non-negative")
    return duration


def _supported_schema_version(value: object) -> str:
    version = _non_empty_string(value, "schema_version")
    if version not in SUPPORTED_RUN_ARTIFACT_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported run artefact schema version {version!r}")
    return version


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{field_name} object keys must be strings")
    return value


def _require_exact_fields(
    value: Mapping[str, object], required_fields: set[str], field_name: str
) -> None:
    missing = sorted(required_fields - value.keys())
    if missing:
        raise ValueError(f"{field_name} is missing field {missing[0]!r}")
    unknown = sorted(value.keys() - required_fields)
    if unknown:
        raise ValueError(f"{field_name} field {unknown[0]!r} is not allowed")


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _non_empty_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if not text.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _json_object(value: object, field_name: str) -> dict[str, JsonValue]:
    mapping = _mapping(value, field_name)
    return {key: _copy_json_value(item, f"{field_name}.{key}") for key, item in mapping.items()}


def _copy_json_value(value: object, field_name: str) -> JsonValue:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} must be a finite JSON number")
        return value
    if isinstance(value, list):
        return [
            _copy_json_value(item, f"{field_name}[{index}]") for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        return _json_object(value, field_name)
    raise TypeError(f"{field_name} must be a JSON value")


def _reject_non_standard_number(value: str) -> NoReturn:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")


def _object_from_unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result
