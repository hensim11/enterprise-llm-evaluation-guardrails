"""Versioned deterministic-evaluation evidence kept separate from raw runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from llm_eval_guardrails.case_schema import AssertionType
from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact

EVALUATION_ARTIFACT_SCHEMA_VERSION = "1"
DETERMINISTIC_EVALUATOR_ID = "deterministic-string-assertions"
DETERMINISTIC_EVALUATOR_VERSION = "1"


class EvaluationOutcome(StrEnum):
    """Explicit evaluation states; none is a raw execution status."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class EvaluationError:
    """Reason deterministic evaluation could not be performed."""

    type: str
    message: str

    def __post_init__(self) -> None:
        _non_empty_string(self.type, "evaluation_error.type")
        _string(self.message, "evaluation_error.message")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {"type": self.type, "message": self.message}

    @classmethod
    def from_mapping(cls, value: object) -> EvaluationError:
        mapping = _mapping(value, "evaluation_error")
        _exact_fields(mapping, {"type", "message"}, "evaluation_error")
        return cls(
            type=_non_empty_string(mapping["type"], "evaluation_error.type"),
            message=_string(mapping["message"], "evaluation_error.message"),
        )


@dataclass(frozen=True, slots=True)
class AssertionEvaluation:
    """Evidence for one literal assertion against a successful raw output."""

    criterion: str
    assertion_type: AssertionType
    expected: str
    outcome: EvaluationOutcome
    explanation: str

    def __post_init__(self) -> None:
        _non_empty_string(self.criterion, "criterion")
        if not isinstance(self.assertion_type, AssertionType):
            raise TypeError("assertion_type must be an AssertionType")
        _non_empty_string(self.expected, "expected")
        if self.outcome not in {
            EvaluationOutcome.PASS,
            EvaluationOutcome.FAIL,
            EvaluationOutcome.ERROR,
        }:
            raise ValueError("assertion outcome must be pass, fail, or error")
        _non_empty_string(self.explanation, "explanation")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "criterion": self.criterion,
            "assertion_type": self.assertion_type.value,
            "expected": self.expected,
            "outcome": self.outcome.value,
            "explanation": self.explanation,
        }

    @classmethod
    def from_mapping(cls, value: object) -> AssertionEvaluation:
        mapping = _mapping(value, "assertions[]")
        _exact_fields(
            mapping,
            {"criterion", "assertion_type", "expected", "outcome", "explanation"},
            "assertions[]",
        )
        try:
            assertion_type = AssertionType(
                _non_empty_string(mapping["assertion_type"], "assertions[].assertion_type")
            )
        except ValueError as error:
            raise ValueError("assertions[].assertion_type is unsupported") from error
        outcome = _outcome(mapping["outcome"], "assertions[].outcome")
        return cls(
            criterion=_non_empty_string(mapping["criterion"], "assertions[].criterion"),
            assertion_type=assertion_type,
            expected=_non_empty_string(mapping["expected"], "assertions[].expected"),
            outcome=outcome,
            explanation=_non_empty_string(mapping["explanation"], "assertions[].explanation"),
        )


@dataclass(frozen=True, slots=True)
class CaseEvaluationResult:
    """Deterministic result for one case, linked to its raw execution state."""

    case_id: str
    execution_status: ExecutionStatus
    outcome: EvaluationOutcome
    assertions: tuple[AssertionEvaluation, ...]
    evaluation_error: EvaluationError | None

    def __post_init__(self) -> None:
        _non_empty_string(self.case_id, "case_id")
        if not isinstance(self.execution_status, ExecutionStatus):
            raise TypeError("execution_status must be an ExecutionStatus")
        if not isinstance(self.outcome, EvaluationOutcome):
            raise TypeError("outcome must be an EvaluationOutcome")
        if not isinstance(self.assertions, tuple) or any(
            not isinstance(item, AssertionEvaluation) for item in self.assertions
        ):
            raise TypeError("assertions must be a tuple of AssertionEvaluation values")
        criteria = [item.criterion for item in self.assertions]
        if len(criteria) != len(set(criteria)):
            raise ValueError("assertions must have unique criteria")

        if self.execution_status is ExecutionStatus.ERROR:
            if self.outcome is not EvaluationOutcome.ERROR:
                raise ValueError("execution error must have evaluation outcome error")
            if not isinstance(self.evaluation_error, EvaluationError):
                raise ValueError("execution error must include evaluation_error")
            if any(item.outcome is not EvaluationOutcome.ERROR for item in self.assertions):
                raise ValueError("execution error assertion outcomes must be error")
            return

        if self.evaluation_error is not None:
            raise ValueError("successful execution must not include evaluation_error")
        if not self.assertions:
            if self.outcome is not EvaluationOutcome.NOT_APPLICABLE:
                raise ValueError("case without assertions must be not_applicable")
        elif self.outcome is EvaluationOutcome.PASS:
            if any(item.outcome is not EvaluationOutcome.PASS for item in self.assertions):
                raise ValueError("passing case must contain only passing assertions")
        elif self.outcome is EvaluationOutcome.FAIL:
            if not any(item.outcome is EvaluationOutcome.FAIL for item in self.assertions):
                raise ValueError("failing case must contain a failed assertion")
            if any(item.outcome is EvaluationOutcome.ERROR for item in self.assertions):
                raise ValueError("failing case must not contain assertion errors")
        elif self.outcome is EvaluationOutcome.ERROR:
            if not any(item.outcome is EvaluationOutcome.ERROR for item in self.assertions):
                raise ValueError("error case must contain an assertion error")
        else:
            raise ValueError("asserted successful case cannot be not_applicable")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "execution_status": self.execution_status.value,
            "outcome": self.outcome.value,
            "assertions": [item.to_mapping() for item in self.assertions],
            "evaluation_error": (
                None if self.evaluation_error is None else self.evaluation_error.to_mapping()
            ),
        }

    @classmethod
    def from_mapping(cls, value: object) -> CaseEvaluationResult:
        mapping = _mapping(value, "results[]")
        _exact_fields(
            mapping,
            {"case_id", "execution_status", "outcome", "assertions", "evaluation_error"},
            "results[]",
        )
        try:
            execution_status = ExecutionStatus(
                _non_empty_string(mapping["execution_status"], "results[].execution_status")
            )
        except ValueError as error:
            raise ValueError("results[].execution_status must be success or error") from error
        raw_assertions = mapping["assertions"]
        if not isinstance(raw_assertions, list):
            raise TypeError("results[].assertions must be an array")
        raw_error = mapping["evaluation_error"]
        return cls(
            case_id=_non_empty_string(mapping["case_id"], "results[].case_id"),
            execution_status=execution_status,
            outcome=_outcome(mapping["outcome"], "results[].outcome"),
            assertions=tuple(AssertionEvaluation.from_mapping(item) for item in raw_assertions),
            evaluation_error=(
                None if raw_error is None else EvaluationError.from_mapping(raw_error)
            ),
        )


@dataclass(frozen=True, slots=True)
class EvaluationArtifact:
    """One complete set of deterministic evidence for a raw run."""

    run_id: str
    dataset_fingerprint: str
    results: tuple[CaseEvaluationResult, ...]
    schema_version: str = EVALUATION_ARTIFACT_SCHEMA_VERSION
    evaluator_id: str = DETERMINISTIC_EVALUATOR_ID
    evaluator_version: str = DETERMINISTIC_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported evaluation artefact schema version {self.schema_version!r}"
            )
        _non_empty_string(self.run_id, "run_id")
        _non_empty_string(self.dataset_fingerprint, "dataset_fingerprint")
        if self.evaluator_id != DETERMINISTIC_EVALUATOR_ID:
            raise ValueError(f"unsupported evaluator id {self.evaluator_id!r}")
        if self.evaluator_version != DETERMINISTIC_EVALUATOR_VERSION:
            raise ValueError(f"unsupported evaluator version {self.evaluator_version!r}")
        if not isinstance(self.results, tuple) or not self.results:
            raise ValueError("results must be a non-empty tuple")
        ids: set[str] = set()
        for index, result in enumerate(self.results):
            if not isinstance(result, CaseEvaluationResult):
                raise TypeError(f"results[{index}] must be a CaseEvaluationResult")
            if result.case_id in ids:
                raise ValueError(f"results[{index}].case_id duplicates {result.case_id!r}")
            ids.add(result.case_id)

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "source_run": {
                "run_id": self.run_id,
                "dataset_fingerprint": self.dataset_fingerprint,
            },
            "evaluator": {"id": self.evaluator_id, "version": self.evaluator_version},
            "results": [result.to_mapping() for result in self.results],
        }

    @classmethod
    def from_mapping(cls, value: object) -> EvaluationArtifact:
        mapping = _mapping(value, "$")
        _exact_fields(mapping, {"schema_version", "source_run", "evaluator", "results"}, "$")
        source = _mapping(mapping["source_run"], "source_run")
        _exact_fields(source, {"run_id", "dataset_fingerprint"}, "source_run")
        evaluator = _mapping(mapping["evaluator"], "evaluator")
        _exact_fields(evaluator, {"id", "version"}, "evaluator")
        raw_results = mapping["results"]
        if not isinstance(raw_results, list):
            raise TypeError("results must be an array")
        return cls(
            schema_version=_non_empty_string(mapping["schema_version"], "schema_version"),
            run_id=_non_empty_string(source["run_id"], "source_run.run_id"),
            dataset_fingerprint=_non_empty_string(
                source["dataset_fingerprint"], "source_run.dataset_fingerprint"
            ),
            evaluator_id=_non_empty_string(evaluator["id"], "evaluator.id"),
            evaluator_version=_non_empty_string(evaluator["version"], "evaluator.version"),
            results=tuple(CaseEvaluationResult.from_mapping(item) for item in raw_results),
        )

    def validate_against(self, raw_run: RunArtifact) -> None:
        """Reject a stale, ambiguous, or non-canonical result for raw evidence."""
        if self.run_id != raw_run.run_id:
            raise ValueError("evaluation source run_id does not match raw run")
        if self.dataset_fingerprint != raw_run.dataset.fingerprint:
            raise ValueError("evaluation dataset fingerprint does not match raw run")
        expected_ids = tuple(case.id for case in raw_run.dataset.cases)
        actual_ids = tuple(result.case_id for result in self.results)
        if actual_ids != expected_ids:
            raise ValueError("evaluation results must match raw case IDs and ordering exactly")
        for index, (case, evaluated, raw) in enumerate(
            zip(raw_run.dataset.cases, self.results, raw_run.results, strict=True)
        ):
            if evaluated.execution_status is not raw.status:
                raise ValueError(
                    f"evaluation results[{index}].execution_status does not match raw result"
                )
            expected_assertions = tuple(
                (assertion.criterion, assertion.type, assertion.value)
                for assertion in case.assertions
            )
            actual_assertions = tuple(
                (assertion.criterion, assertion.assertion_type, assertion.expected)
                for assertion in evaluated.assertions
            )
            if actual_assertions != expected_assertions:
                raise ValueError(
                    f"evaluation results[{index}].assertions do not match raw case snapshot"
                )
        # Local import avoids a module cycle while keeping evaluator semantics in one place.
        from llm_eval_guardrails.evaluator import evaluate_run

        canonical = evaluate_run(raw_run)
        for index, (stored, recomputed) in enumerate(
            zip(self.results, canonical.results, strict=True)
        ):
            if stored != recomputed:
                raise ValueError(
                    f"evaluation results[{index}] does not match canonical deterministic "
                    "recomputation from the raw run"
                )


def write_evaluation_artifact(artifact: EvaluationArtifact, path: str | Path) -> None:
    """Write validated evidence to a new file without overwriting."""
    if not isinstance(artifact, EvaluationArtifact):
        raise TypeError("artifact must be an EvaluationArtifact")
    serialized = json.dumps(artifact.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized + "\n")


def load_evaluation_artifact(
    path: str | Path, *, raw_run: RunArtifact | None = None
) -> EvaluationArtifact:
    """Load and validate evaluated evidence, optionally reconciling its raw join."""
    with Path(path).open("r", encoding="utf-8") as source:
        value = json.load(
            source,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_non_standard_number,
        )
    artifact = EvaluationArtifact.from_mapping(value)
    if raw_run is not None:
        artifact.validate_against(raw_run)
    return artifact


def _outcome(value: object, field_name: str) -> EvaluationOutcome:
    try:
        return EvaluationOutcome(_non_empty_string(value, field_name))
    except ValueError as error:
        raise ValueError(f"{field_name} is unsupported") from error


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return value


def _exact_fields(value: Mapping[str, object], fields: set[str], name: str) -> None:
    missing = sorted(fields - value.keys())
    if missing:
        raise ValueError(f"{name} is missing field {missing[0]!r}")
    unknown = sorted(value.keys() - fields)
    if unknown:
        raise ValueError(f"{name} field {unknown[0]!r} is not allowed")


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _non_empty_string(value: object, field_name: str) -> str:
    text = _string(value, field_name)
    if not text.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")
