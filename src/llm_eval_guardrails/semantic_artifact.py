"""Versioned semantic-judge evidence kept separate from raw and deterministic runs."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import NoReturn

from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact

SEMANTIC_ARTIFACT_SCHEMA_VERSION = "1"
SEMANTIC_RUBRIC_ID = "authored-expected-behaviour"
SEMANTIC_RUBRIC_VERSION = "1"
SEMANTIC_PROMPT_VERSION = "semantic-judge-v1"
SEMANTIC_OUTPUT_SCHEMA_VERSION = "1"


class SemanticOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class JudgeConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FailureMode(StrEnum):
    MATERIAL_CONTRADICTION = "material_contradiction"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    UNSAFE_COMPLIANCE = "unsafe_compliance"
    SENSITIVE_DISCLOSURE = "sensitive_disclosure"
    PROMPT_INJECTION_FOLLOWING = "prompt_injection_following"
    INAPPROPRIATE_REFUSAL = "inappropriate_refusal"
    OMITTED_REQUIRED_BOUNDARY_OR_HELPFUL_ACTION = "omitted_required_boundary_or_helpful_action"
    OTHER_MATERIAL_FAILURE = "other_material_failure"


@dataclass(frozen=True, slots=True)
class ProviderTokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.input_tokens is self.output_tokens is self.total_tokens is None:
            raise ValueError("token usage must contain at least one provider-supplied field")
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise TypeError(f"usage.{name} must be an integer or null")
            if value is not None and value < 0:
                raise ValueError(f"usage.{name} must be non-negative")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_mapping(cls, value: object) -> ProviderTokenUsage:
        mapping = _mapping(value, "usage")
        _exact_fields(mapping, {"input_tokens", "output_tokens", "total_tokens"}, "usage")
        return cls(
            input_tokens=mapping["input_tokens"],
            output_tokens=mapping["output_tokens"],
            total_tokens=mapping["total_tokens"],
        )


@dataclass(frozen=True, slots=True)
class SemanticEvaluationError:
    type: str
    message: str

    def __post_init__(self) -> None:
        _non_empty_string(self.type, "semantic_error.type")
        _string(self.message, "semantic_error.message")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {"type": self.type, "message": self.message}

    @classmethod
    def from_mapping(cls, value: object) -> SemanticEvaluationError:
        mapping = _mapping(value, "semantic_error")
        _exact_fields(mapping, {"type", "message"}, "semantic_error")
        return cls(
            type=_non_empty_string(mapping["type"], "semantic_error.type"),
            message=_string(mapping["message"], "semantic_error.message"),
        )


@dataclass(frozen=True, slots=True)
class SemanticJudgment:
    """A completed provider-neutral structural judge return value."""

    outcome: SemanticOutcome
    confidence: JudgeConfidence
    rationale: str
    response_evidence: tuple[str, ...] = ()
    failure_modes: tuple[FailureMode, ...] = ()
    usage: ProviderTokenUsage | None = None

    def __post_init__(self) -> None:
        if self.outcome not in {SemanticOutcome.PASS, SemanticOutcome.FAIL}:
            raise ValueError("completed judgement outcome must be pass or fail")
        if not isinstance(self.confidence, JudgeConfidence):
            raise TypeError("confidence must be JudgeConfidence")
        _non_empty_string(self.rationale, "rationale")
        if not isinstance(self.response_evidence, tuple):
            raise TypeError("response_evidence must be a tuple")
        if len(self.response_evidence) > 3:
            raise ValueError("response_evidence must contain at most three excerpts")
        for excerpt in self.response_evidence:
            _non_empty_string(excerpt, "response_evidence[]")
        if len(self.response_evidence) != len(set(self.response_evidence)):
            raise ValueError("response_evidence must not contain duplicates")
        if not isinstance(self.failure_modes, tuple) or any(
            not isinstance(item, FailureMode) for item in self.failure_modes
        ):
            raise TypeError("failure_modes must be a tuple of FailureMode values")
        if len(self.failure_modes) != len(set(self.failure_modes)):
            raise ValueError("failure_modes must not contain duplicates")
        if self.outcome is SemanticOutcome.PASS and self.failure_modes:
            raise ValueError("passing judgement must not contain failure modes")
        if self.outcome is SemanticOutcome.FAIL and not self.failure_modes:
            raise ValueError("failing judgement must contain at least one failure mode")
        if self.usage is not None and not isinstance(self.usage, ProviderTokenUsage):
            raise TypeError("usage must be ProviderTokenUsage or None")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "outcome": self.outcome.value,
            "confidence": self.confidence.value,
            "rationale": self.rationale,
            "response_evidence": list(self.response_evidence),
            "failure_modes": [item.value for item in self.failure_modes],
        }

    @classmethod
    def from_mapping(cls, value: object) -> SemanticJudgment:
        mapping = _mapping(value, "judgement")
        _exact_fields(
            mapping,
            {"outcome", "confidence", "rationale", "response_evidence", "failure_modes"},
            "judgement",
        )
        evidence = _string_array(mapping["response_evidence"], "response_evidence")
        raw_modes = _string_array(mapping["failure_modes"], "failure_modes")
        try:
            outcome = SemanticOutcome(_non_empty_string(mapping["outcome"], "outcome"))
        except ValueError as error:
            raise ValueError("outcome must be pass or fail") from error
        try:
            confidence = JudgeConfidence(_non_empty_string(mapping["confidence"], "confidence"))
        except ValueError as error:
            raise ValueError("confidence must be low, medium, or high") from error
        try:
            failure_modes = tuple(FailureMode(item) for item in raw_modes)
        except ValueError as error:
            raise ValueError("failure_modes contains an unsupported value") from error
        return cls(
            outcome=outcome,
            confidence=confidence,
            rationale=_non_empty_string(mapping["rationale"], "rationale"),
            response_evidence=evidence,
            failure_modes=failure_modes,
        )


@dataclass(frozen=True, slots=True)
class SemanticCaseResult:
    case_id: str
    raw_result_index: int
    execution_status: ExecutionStatus
    outcome: SemanticOutcome
    duration_seconds: float
    confidence: JudgeConfidence | None
    rationale: str | None
    response_evidence: tuple[str, ...]
    failure_modes: tuple[FailureMode, ...]
    semantic_error: SemanticEvaluationError | None
    usage: ProviderTokenUsage | None

    def __post_init__(self) -> None:
        _non_empty_string(self.case_id, "case_id")
        if isinstance(self.raw_result_index, bool) or not isinstance(self.raw_result_index, int):
            raise TypeError("raw_result_index must be an integer")
        if self.raw_result_index < 0:
            raise ValueError("raw_result_index must be non-negative")
        if not isinstance(self.execution_status, ExecutionStatus):
            raise TypeError("execution_status must be ExecutionStatus")
        if not isinstance(self.outcome, SemanticOutcome):
            raise TypeError("outcome must be SemanticOutcome")
        _duration(self.duration_seconds)
        if not isinstance(self.response_evidence, tuple):
            raise TypeError("response_evidence must be a tuple")
        if len(self.response_evidence) > 3 or len(set(self.response_evidence)) != len(
            self.response_evidence
        ):
            raise ValueError("response_evidence must contain at most three unique excerpts")
        for excerpt in self.response_evidence:
            _non_empty_string(excerpt, "response_evidence[]")
        if not isinstance(self.failure_modes, tuple) or any(
            not isinstance(mode, FailureMode) for mode in self.failure_modes
        ):
            raise TypeError("failure_modes must be a tuple of FailureMode values")
        if len(set(self.failure_modes)) != len(self.failure_modes):
            raise ValueError("failure_modes must not contain duplicates")

        completed = self.outcome in {SemanticOutcome.PASS, SemanticOutcome.FAIL}
        if completed:
            if self.execution_status is not ExecutionStatus.SUCCESS:
                raise ValueError("completed semantic result requires successful execution")
            if not isinstance(self.confidence, JudgeConfidence):
                raise ValueError("completed semantic result requires confidence")
            if self.rationale is None:
                raise ValueError("completed semantic result requires rationale")
            _non_empty_string(self.rationale, "rationale")
            if self.semantic_error is not None:
                raise ValueError("completed semantic result must not contain semantic_error")
            if self.outcome is SemanticOutcome.PASS and self.failure_modes:
                raise ValueError("passing semantic result must not contain failure modes")
            if self.outcome is SemanticOutcome.FAIL and not self.failure_modes:
                raise ValueError("failing semantic result requires at least one failure mode")
        else:
            if self.confidence is not None or self.response_evidence or self.failure_modes:
                raise ValueError("error/not_applicable result must not contain judge fields")
            if self.usage is not None:
                raise ValueError("error/not_applicable result must not contain token usage")
            if self.outcome is SemanticOutcome.ERROR:
                if not isinstance(self.semantic_error, SemanticEvaluationError):
                    raise ValueError("error semantic result requires semantic_error")
                if self.rationale is not None:
                    raise ValueError("error semantic result must not contain rationale")
            elif self.outcome is SemanticOutcome.NOT_APPLICABLE:
                if self.execution_status is not ExecutionStatus.SUCCESS:
                    raise ValueError("not_applicable requires successful execution")
                if self.semantic_error is not None:
                    raise ValueError("not_applicable must not contain semantic_error")
                if self.rationale is None:
                    raise ValueError("not_applicable requires an explicit rationale")
                _non_empty_string(self.rationale, "rationale")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "raw_result_index": self.raw_result_index,
            "execution_status": self.execution_status.value,
            "outcome": self.outcome.value,
            "confidence": None if self.confidence is None else self.confidence.value,
            "rationale": self.rationale,
            "response_evidence": list(self.response_evidence),
            "failure_modes": [item.value for item in self.failure_modes],
            "duration_seconds": self.duration_seconds,
            "semantic_error": (
                None if self.semantic_error is None else self.semantic_error.to_mapping()
            ),
            "usage": None if self.usage is None else self.usage.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, value: object) -> SemanticCaseResult:
        mapping = _mapping(value, "results[]")
        _exact_fields(
            mapping,
            {
                "case_id",
                "raw_result_index",
                "execution_status",
                "outcome",
                "confidence",
                "rationale",
                "response_evidence",
                "failure_modes",
                "duration_seconds",
                "semantic_error",
                "usage",
            },
            "results[]",
        )
        try:
            execution_status = ExecutionStatus(
                _non_empty_string(mapping["execution_status"], "execution_status")
            )
        except ValueError as error:
            raise ValueError("execution_status is unsupported") from error
        try:
            outcome = SemanticOutcome(_non_empty_string(mapping["outcome"], "outcome"))
        except ValueError as error:
            raise ValueError("semantic outcome is unsupported") from error
        confidence_value = mapping["confidence"]
        try:
            confidence = (
                None
                if confidence_value is None
                else JudgeConfidence(_non_empty_string(confidence_value, "confidence"))
            )
        except ValueError as error:
            raise ValueError("confidence is unsupported") from error
        try:
            modes = tuple(
                FailureMode(item)
                for item in _string_array(mapping["failure_modes"], "failure_modes")
            )
        except ValueError as error:
            raise ValueError("failure_modes contains an unsupported value") from error
        error_value = mapping["semantic_error"]
        usage_value = mapping["usage"]
        rationale = mapping["rationale"]
        return cls(
            case_id=_non_empty_string(mapping["case_id"], "case_id"),
            raw_result_index=mapping["raw_result_index"],
            execution_status=execution_status,
            outcome=outcome,
            duration_seconds=_duration(mapping["duration_seconds"]),
            confidence=confidence,
            rationale=None if rationale is None else _string(rationale, "rationale"),
            response_evidence=_string_array(mapping["response_evidence"], "response_evidence"),
            failure_modes=modes,
            semantic_error=(
                None if error_value is None else SemanticEvaluationError.from_mapping(error_value)
            ),
            usage=None if usage_value is None else ProviderTokenUsage.from_mapping(usage_value),
        )


@dataclass(frozen=True, slots=True)
class JudgeProvenance:
    id: str
    configuration: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _non_empty_string(self.id, "judge.id")
        object.__setattr__(
            self, "configuration", _json_object(self.configuration, "judge.configuration")
        )

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "id": self.id,
            "configuration": _json_object(self.configuration, "judge.configuration"),
        }

    @classmethod
    def from_mapping(cls, value: object) -> JudgeProvenance:
        mapping = _mapping(value, "judge")
        _exact_fields(mapping, {"id", "configuration"}, "judge")
        return cls(
            id=_non_empty_string(mapping["id"], "judge.id"),
            configuration=_json_object(mapping["configuration"], "judge.configuration"),
        )


@dataclass(frozen=True, slots=True)
class SemanticEvaluationArtifact:
    run_id: str
    dataset_fingerprint: str
    judge: JudgeProvenance
    results: tuple[SemanticCaseResult, ...]
    schema_version: str = SEMANTIC_ARTIFACT_SCHEMA_VERSION
    rubric_id: str = SEMANTIC_RUBRIC_ID
    rubric_version: str = SEMANTIC_RUBRIC_VERSION
    prompt_version: str = SEMANTIC_PROMPT_VERSION
    output_schema_version: str = SEMANTIC_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SEMANTIC_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported semantic artefact schema version {self.schema_version!r}"
            )
        if (self.rubric_id, self.rubric_version) != (SEMANTIC_RUBRIC_ID, SEMANTIC_RUBRIC_VERSION):
            raise ValueError("unsupported semantic rubric identity or version")
        if self.prompt_version != SEMANTIC_PROMPT_VERSION:
            raise ValueError("unsupported semantic prompt version")
        if self.output_schema_version != SEMANTIC_OUTPUT_SCHEMA_VERSION:
            raise ValueError("unsupported semantic output-schema version")
        _non_empty_string(self.run_id, "run_id")
        _non_empty_string(self.dataset_fingerprint, "dataset_fingerprint")
        if not isinstance(self.judge, JudgeProvenance):
            raise TypeError("judge must be JudgeProvenance")
        if not isinstance(self.results, tuple) or not self.results:
            raise ValueError("results must be a non-empty tuple")
        ids: set[str] = set()
        indices: set[int] = set()
        previous_index = -1
        for index, result in enumerate(self.results):
            if not isinstance(result, SemanticCaseResult):
                raise TypeError(f"results[{index}] must be SemanticCaseResult")
            if result.case_id in ids:
                raise ValueError(f"results[{index}].case_id duplicates {result.case_id!r}")
            if result.raw_result_index in indices:
                raise ValueError(f"results[{index}].raw_result_index is duplicated")
            if result.raw_result_index <= previous_index:
                raise ValueError("semantic results must preserve raw-result index ordering")
            ids.add(result.case_id)
            indices.add(result.raw_result_index)
            previous_index = result.raw_result_index

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "rubric": {"id": self.rubric_id, "version": self.rubric_version},
            "prompt_version": self.prompt_version,
            "output_schema_version": self.output_schema_version,
            "source_run": {
                "run_id": self.run_id,
                "dataset_fingerprint": self.dataset_fingerprint,
            },
            "judge": self.judge.to_mapping(),
            "results": [result.to_mapping() for result in self.results],
        }

    @classmethod
    def from_mapping(cls, value: object) -> SemanticEvaluationArtifact:
        mapping = _mapping(value, "$")
        _exact_fields(
            mapping,
            {
                "schema_version",
                "rubric",
                "prompt_version",
                "output_schema_version",
                "source_run",
                "judge",
                "results",
            },
            "$",
        )
        rubric = _mapping(mapping["rubric"], "rubric")
        _exact_fields(rubric, {"id", "version"}, "rubric")
        source = _mapping(mapping["source_run"], "source_run")
        _exact_fields(source, {"run_id", "dataset_fingerprint"}, "source_run")
        raw_results = mapping["results"]
        if not isinstance(raw_results, list):
            raise TypeError("results must be an array")
        return cls(
            schema_version=_non_empty_string(mapping["schema_version"], "schema_version"),
            rubric_id=_non_empty_string(rubric["id"], "rubric.id"),
            rubric_version=_non_empty_string(rubric["version"], "rubric.version"),
            prompt_version=_non_empty_string(mapping["prompt_version"], "prompt_version"),
            output_schema_version=_non_empty_string(
                mapping["output_schema_version"], "output_schema_version"
            ),
            run_id=_non_empty_string(source["run_id"], "source_run.run_id"),
            dataset_fingerprint=_non_empty_string(
                source["dataset_fingerprint"], "source_run.dataset_fingerprint"
            ),
            judge=JudgeProvenance.from_mapping(mapping["judge"]),
            results=tuple(SemanticCaseResult.from_mapping(item) for item in raw_results),
        )

    def validate_against(self, raw_run: RunArtifact) -> None:
        if self.run_id != raw_run.run_id:
            raise ValueError("semantic source run_id does not match raw run")
        if self.dataset_fingerprint != raw_run.dataset.fingerprint:
            raise ValueError("semantic dataset fingerprint does not match raw run")
        previous_index = -1
        for result_index, result in enumerate(self.results):
            if result.raw_result_index <= previous_index:
                raise ValueError("semantic results must preserve raw case ordering")
            previous_index = result.raw_result_index
            if result.raw_result_index >= len(raw_run.results):
                raise ValueError(
                    f"semantic results[{result_index}] references an unknown raw index"
                )
            raw = raw_run.results[result.raw_result_index]
            case = raw_run.dataset.cases[result.raw_result_index]
            if result.case_id != case.id:
                raise ValueError(f"semantic results[{result_index}] case/index join is invalid")
            if result.execution_status is not raw.status:
                raise ValueError(
                    f"semantic results[{result_index}] execution status does not match raw"
                )
            if raw.status is ExecutionStatus.ERROR:
                if (
                    result.outcome is not SemanticOutcome.ERROR
                    or result.semantic_error is None
                    or result.semantic_error.type != "raw_execution_error"
                ):
                    raise ValueError(
                        "raw execution errors must be preserved without judge evaluation"
                    )
            elif case.expected_behavior is None:
                if result.outcome is not SemanticOutcome.NOT_APPLICABLE:
                    raise ValueError("case without expected behaviour must be not_applicable")
            elif result.outcome is SemanticOutcome.NOT_APPLICABLE:
                raise ValueError("case with expected behaviour must not be not_applicable")
            if raw.output is not None:
                for excerpt in result.response_evidence:
                    if excerpt not in raw.output:
                        raise ValueError(
                            f"semantic results[{result_index}] response evidence is not an "
                            "exact raw-output substring"
                        )


def write_semantic_artifact(artifact: SemanticEvaluationArtifact, path: str | Path) -> None:
    if not isinstance(artifact, SemanticEvaluationArtifact):
        raise TypeError("artifact must be SemanticEvaluationArtifact")
    serialized = json.dumps(artifact.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized + "\n")


def load_semantic_artifact(
    path: str | Path, *, raw_run: RunArtifact | None = None
) -> SemanticEvaluationArtifact:
    with Path(path).open("r", encoding="utf-8") as source:
        value = json.load(
            source, object_pairs_hook=_unique_object, parse_constant=_reject_non_standard_number
        )
    artifact = SemanticEvaluationArtifact.from_mapping(value)
    if raw_run is not None:
        artifact.validate_against(raw_run)
    return artifact


def _duration(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("duration_seconds must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("duration_seconds must be finite and non-negative")
    return result


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} object keys must be strings")
    return value


def _exact_fields(value: Mapping[str, object], fields: set[str], name: str) -> None:
    missing = sorted(fields - value.keys())
    if missing:
        raise ValueError(f"{name} is missing field {missing[0]!r}")
    unknown = sorted(value.keys() - fields)
    if unknown:
        raise ValueError(f"{name} field {unknown[0]!r} is not allowed")


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _non_empty_string(value: object, name: str) -> str:
    text = _string(value, name)
    if not text.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return text


def _string_array(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an array")
    return tuple(_non_empty_string(item, f"{name}[]") for item in value)


def _json_object(value: object, name: str) -> dict[str, JsonValue]:
    mapping = _mapping(value, name)
    return {key: _json_value(item, f"{name}.{key}") for key, item in mapping.items()}


def _json_value(value: object, name: str) -> JsonValue:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite JSON number")
        return value
    if isinstance(value, list):
        return [_json_value(item, f"{name}[]") for item in value]
    if isinstance(value, Mapping):
        return _json_object(value, name)
    raise TypeError(f"{name} must be a JSON value")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> NoReturn:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")
