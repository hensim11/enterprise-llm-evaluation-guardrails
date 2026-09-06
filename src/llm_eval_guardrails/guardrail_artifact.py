"""Versioned runtime-guardrail decisions kept separate from raw/evaluated evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from llm_eval_guardrails.guardrails import (
    DETECTORS,
    EXECUTION_ERROR_EXPLANATION,
    GUARDRAIL_POLICY_ID,
    GUARDRAIL_POLICY_VERSION,
    INPUT_BLOCK_EXPLANATION,
    PASS_RELEASE_EXPLANATION,
    RESPONSE_BLOCK_EXPLANATION,
    WARN_RELEASE_EXPLANATION,
    DetectorTrigger,
    DetectorVersion,
    GuardrailDecision,
    GuardrailStage,
    NorthstarGuardrailPolicy,
    candidate_sha256,
    final_decision,
    response_leak_trigger,
)
from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact
from llm_eval_guardrails.system_under_test import SystemRequest

GUARDRAIL_ARTIFACT_SCHEMA_VERSION = "1"


class ObservedOutputSource(StrEnum):
    """How the externally observed raw output was produced."""

    UNDERLYING_MODEL = "underlying_model"
    INPUT_BLOCK_RESPONSE = "input_block_response"
    RESPONSE_BLOCK_RESPONSE = "response_block_response"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True, slots=True)
class GuardrailCaseDecision:
    """Complete guardrail evidence for one raw-run case."""

    case_id: str
    policy_id: str
    policy_version: str
    detector_versions: tuple[DetectorVersion, ...]
    triggered_detectors: tuple[DetectorTrigger, ...]
    final_decision: GuardrailDecision
    underlying_model_invoked: bool
    candidate_response_released: bool
    candidate_response_replaced: bool
    candidate_response_sha256: str | None
    observed_output_source: ObservedOutputSource
    replacement_response_id: str | None
    replacement_response_version: str | None
    explanation: str

    def __post_init__(self) -> None:
        _non_empty(self.case_id, "case_id")
        _non_empty(self.policy_id, "policy_id")
        _non_empty(self.policy_version, "policy_version")
        if not isinstance(self.detector_versions, tuple) or any(
            not isinstance(item, DetectorVersion) for item in self.detector_versions
        ):
            raise TypeError("detector_versions must contain DetectorVersion values")
        if not isinstance(self.triggered_detectors, tuple) or any(
            not isinstance(item, DetectorTrigger) for item in self.triggered_detectors
        ):
            raise TypeError("triggered_detectors must contain DetectorTrigger values")
        if not isinstance(self.final_decision, GuardrailDecision):
            raise TypeError("final_decision must be a GuardrailDecision")
        for name in (
            "underlying_model_invoked",
            "candidate_response_released",
            "candidate_response_replaced",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean")
        if not isinstance(self.observed_output_source, ObservedOutputSource):
            raise TypeError("observed_output_source must be an ObservedOutputSource")
        _non_empty(self.explanation, "explanation")
        if self.candidate_response_sha256 is not None and not _sha256(
            self.candidate_response_sha256
        ):
            raise ValueError("candidate_response_sha256 must be a lowercase SHA-256 digest")
        if (self.replacement_response_id is None) != (self.replacement_response_version is None):
            raise ValueError("replacement response ID and version must both be set or both be null")
        if self.replacement_response_id is not None:
            _non_empty(self.replacement_response_id, "replacement_response_id")
            _non_empty(self.replacement_response_version, "replacement_response_version")
        if self.final_decision is not final_decision(self.triggered_detectors):
            raise ValueError("final_decision does not follow BLOCK > WARN > PASS precedence")
        self._validate_state()

    def _validate_state(self) -> None:
        source = self.observed_output_source
        if source is ObservedOutputSource.INPUT_BLOCK_RESPONSE:
            if self.final_decision is not GuardrailDecision.BLOCK:
                raise ValueError("input block response requires final decision block")
            if self.underlying_model_invoked:
                raise ValueError("input block must not invoke the underlying model")
            if self.candidate_response_sha256 is not None:
                raise ValueError("input block must not record a candidate response digest")
            if self.candidate_response_released or self.candidate_response_replaced:
                raise ValueError("input block has no candidate response to release or replace")
            if self.replacement_response_id is None:
                raise ValueError("input block must identify its versioned replacement response")
        elif source is ObservedOutputSource.RESPONSE_BLOCK_RESPONSE:
            if self.final_decision is not GuardrailDecision.BLOCK:
                raise ValueError("response block response requires final decision block")
            if not self.underlying_model_invoked or not self.candidate_response_replaced:
                raise ValueError("response block must invoke the model and replace its candidate")
            if self.candidate_response_released or self.candidate_response_sha256 is None:
                raise ValueError("response block must withhold a digested candidate response")
            if self.replacement_response_id is None:
                raise ValueError("response block must identify its versioned replacement response")
        elif source is ObservedOutputSource.UNDERLYING_MODEL:
            if not self.underlying_model_invoked or not self.candidate_response_released:
                raise ValueError("released output must come from an invoked underlying model")
            if self.candidate_response_replaced or self.candidate_response_sha256 is None:
                raise ValueError("released output must have a digest and not be replaced")
            if self.replacement_response_id is not None:
                raise ValueError("released output must not identify a replacement response")
        else:
            if not self.underlying_model_invoked:
                raise ValueError("execution error must follow an underlying-model invocation")
            if self.candidate_response_released or self.candidate_response_replaced:
                raise ValueError("execution error has no candidate to release or replace")
            if self.candidate_response_sha256 is not None:
                raise ValueError("execution error must not record a candidate response digest")
            if self.replacement_response_id is not None:
                raise ValueError("execution error must not identify a replacement response")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "case_id": self.case_id,
            "policy": {"id": self.policy_id, "version": self.policy_version},
            "detector_versions": [
                _detector_version_mapping(item) for item in self.detector_versions
            ],
            "triggered_detectors": [_trigger_mapping(item) for item in self.triggered_detectors],
            "final_decision": self.final_decision.value,
            "underlying_model_invoked": self.underlying_model_invoked,
            "candidate_response_released": self.candidate_response_released,
            "candidate_response_replaced": self.candidate_response_replaced,
            "candidate_response_sha256": self.candidate_response_sha256,
            "observed_output_source": self.observed_output_source.value,
            "replacement_response": (
                None
                if self.replacement_response_id is None
                else {
                    "id": self.replacement_response_id,
                    "version": self.replacement_response_version,
                }
            ),
            "explanation": self.explanation,
        }

    @classmethod
    def from_mapping(cls, value: object) -> GuardrailCaseDecision:
        mapping = _mapping(value, "decisions[]")
        _exact_fields(
            mapping,
            {
                "case_id",
                "policy",
                "detector_versions",
                "triggered_detectors",
                "final_decision",
                "underlying_model_invoked",
                "candidate_response_released",
                "candidate_response_replaced",
                "candidate_response_sha256",
                "observed_output_source",
                "replacement_response",
                "explanation",
            },
            "decisions[]",
        )
        policy = _mapping(mapping["policy"], "decisions[].policy")
        _exact_fields(policy, {"id", "version"}, "decisions[].policy")
        versions = _array(mapping["detector_versions"], "decisions[].detector_versions")
        triggers = _array(mapping["triggered_detectors"], "decisions[].triggered_detectors")
        replacement = mapping["replacement_response"]
        replacement_id = replacement_version = None
        if replacement is not None:
            replacement_mapping = _mapping(replacement, "decisions[].replacement_response")
            _exact_fields(
                replacement_mapping,
                {"id", "version"},
                "decisions[].replacement_response",
            )
            replacement_id = _non_empty(
                replacement_mapping["id"], "decisions[].replacement_response.id"
            )
            replacement_version = _non_empty(
                replacement_mapping["version"], "decisions[].replacement_response.version"
            )
        digest = mapping["candidate_response_sha256"]
        if digest is not None:
            digest = _non_empty(digest, "decisions[].candidate_response_sha256")
        return cls(
            case_id=_non_empty(mapping["case_id"], "decisions[].case_id"),
            policy_id=_non_empty(policy["id"], "decisions[].policy.id"),
            policy_version=_non_empty(policy["version"], "decisions[].policy.version"),
            detector_versions=tuple(_detector_version(item) for item in versions),
            triggered_detectors=tuple(_trigger(item) for item in triggers),
            final_decision=_decision(mapping["final_decision"], "decisions[].final_decision"),
            underlying_model_invoked=_boolean(
                mapping["underlying_model_invoked"], "decisions[].underlying_model_invoked"
            ),
            candidate_response_released=_boolean(
                mapping["candidate_response_released"], "decisions[].candidate_response_released"
            ),
            candidate_response_replaced=_boolean(
                mapping["candidate_response_replaced"], "decisions[].candidate_response_replaced"
            ),
            candidate_response_sha256=digest,
            observed_output_source=_output_source(mapping["observed_output_source"]),
            replacement_response_id=replacement_id,
            replacement_response_version=replacement_version,
            explanation=_non_empty(mapping["explanation"], "decisions[].explanation"),
        )


@dataclass(frozen=True, slots=True)
class GuardrailDecisionArtifact:
    """One complete ordered decision set for a guardrailed raw run."""

    run_id: str
    dataset_fingerprint: str
    decisions: tuple[GuardrailCaseDecision, ...]
    schema_version: str = GUARDRAIL_ARTIFACT_SCHEMA_VERSION
    policy_id: str = GUARDRAIL_POLICY_ID
    policy_version: str = GUARDRAIL_POLICY_VERSION
    detector_versions: tuple[DetectorVersion, ...] = DETECTORS

    def __post_init__(self) -> None:
        if self.schema_version != GUARDRAIL_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported guardrail artefact schema version {self.schema_version!r}"
            )
        _non_empty(self.run_id, "run_id")
        _non_empty(self.dataset_fingerprint, "dataset_fingerprint")
        if (self.policy_id, self.policy_version) != (
            GUARDRAIL_POLICY_ID,
            GUARDRAIL_POLICY_VERSION,
        ):
            raise ValueError("unsupported guardrail policy identity or version")
        if self.detector_versions != DETECTORS:
            raise ValueError("unsupported or non-canonical detector versions")
        if not isinstance(self.decisions, tuple) or not self.decisions:
            raise ValueError("decisions must be a non-empty tuple")
        ids: set[str] = set()
        for index, decision in enumerate(self.decisions):
            if not isinstance(decision, GuardrailCaseDecision):
                raise TypeError(f"decisions[{index}] must be a GuardrailCaseDecision")
            if decision.case_id in ids:
                raise ValueError(f"decisions[{index}].case_id duplicates {decision.case_id!r}")
            ids.add(decision.case_id)
            if (decision.policy_id, decision.policy_version) != (
                self.policy_id,
                self.policy_version,
            ):
                raise ValueError("every case decision must record the artefact policy version")
            if decision.detector_versions != self.detector_versions:
                raise ValueError("every case decision must record the artefact detector versions")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "source_run": {
                "run_id": self.run_id,
                "dataset_fingerprint": self.dataset_fingerprint,
            },
            "policy": {"id": self.policy_id, "version": self.policy_version},
            "detectors": [_detector_version_mapping(item) for item in self.detector_versions],
            "decisions": [decision.to_mapping() for decision in self.decisions],
        }

    @classmethod
    def from_mapping(cls, value: object) -> GuardrailDecisionArtifact:
        mapping = _mapping(value, "$")
        _exact_fields(
            mapping, {"schema_version", "source_run", "policy", "detectors", "decisions"}, "$"
        )
        source = _mapping(mapping["source_run"], "source_run")
        policy = _mapping(mapping["policy"], "policy")
        _exact_fields(source, {"run_id", "dataset_fingerprint"}, "source_run")
        _exact_fields(policy, {"id", "version"}, "policy")
        return cls(
            schema_version=_non_empty(mapping["schema_version"], "schema_version"),
            run_id=_non_empty(source["run_id"], "source_run.run_id"),
            dataset_fingerprint=_non_empty(
                source["dataset_fingerprint"], "source_run.dataset_fingerprint"
            ),
            policy_id=_non_empty(policy["id"], "policy.id"),
            policy_version=_non_empty(policy["version"], "policy.version"),
            detector_versions=tuple(
                _detector_version(item) for item in _array(mapping["detectors"], "detectors")
            ),
            decisions=tuple(
                GuardrailCaseDecision.from_mapping(item)
                for item in _array(mapping["decisions"], "decisions")
            ),
        )

    def validate_against(self, raw_run: RunArtifact) -> None:
        """Require exact joins and canonical decisions wherever evidence permits."""
        if self.run_id != raw_run.run_id:
            raise ValueError("guardrail source run_id does not match raw run")
        if self.dataset_fingerprint != raw_run.dataset.fingerprint:
            raise ValueError("guardrail dataset fingerprint does not match raw run")
        expected_ids = tuple(case.id for case in raw_run.dataset.cases)
        actual_ids = tuple(decision.case_id for decision in self.decisions)
        if actual_ids != expected_ids:
            raise ValueError("guardrail decisions must match raw case IDs and ordering exactly")
        policy = NorthstarGuardrailPolicy()
        for index, (case, raw, decision) in enumerate(
            zip(raw_run.dataset.cases, raw_run.results, self.decisions, strict=True)
        ):
            request = SystemRequest(case.input, case.context)
            input_assessment = policy.inspect_input(request)
            input_triggers = tuple(
                trigger
                for trigger in decision.triggered_detectors
                if trigger.stage is GuardrailStage.INPUT
            )
            if input_triggers != input_assessment.triggers:
                raise ValueError(f"guardrail decisions[{index}] has non-canonical input triggers")
            if (
                input_assessment.decision is GuardrailDecision.BLOCK
                and decision.observed_output_source is not ObservedOutputSource.INPUT_BLOCK_RESPONSE
            ):
                raise ValueError(
                    f"guardrail decisions[{index}] must enforce the canonical input block"
                )
            if decision.observed_output_source in {
                ObservedOutputSource.INPUT_BLOCK_RESPONSE,
                ObservedOutputSource.EXECUTION_ERROR,
            } and any(
                trigger.stage is GuardrailStage.RESPONSE for trigger in decision.triggered_detectors
            ):
                raise ValueError(
                    f"guardrail decisions[{index}] records a response trigger without a candidate"
                )
            self._validate_case(index, raw.status, raw.output, decision, request, policy)
            expected_explanation = {
                ObservedOutputSource.INPUT_BLOCK_RESPONSE: INPUT_BLOCK_EXPLANATION,
                ObservedOutputSource.RESPONSE_BLOCK_RESPONSE: RESPONSE_BLOCK_EXPLANATION,
                ObservedOutputSource.EXECUTION_ERROR: EXECUTION_ERROR_EXPLANATION,
                ObservedOutputSource.UNDERLYING_MODEL: (
                    WARN_RELEASE_EXPLANATION
                    if decision.final_decision is GuardrailDecision.WARN
                    else PASS_RELEASE_EXPLANATION
                ),
            }[decision.observed_output_source]
            if decision.explanation != expected_explanation:
                raise ValueError(f"guardrail decisions[{index}] explanation is non-canonical")

    @staticmethod
    def _validate_case(
        index: int,
        status: ExecutionStatus,
        output: str | None,
        decision: GuardrailCaseDecision,
        request: SystemRequest,
        policy: NorthstarGuardrailPolicy,
    ) -> None:
        source = decision.observed_output_source
        if source is ObservedOutputSource.INPUT_BLOCK_RESPONSE:
            response_id, version, expected_output = policy.input_block_response(
                tuple(
                    trigger
                    for trigger in decision.triggered_detectors
                    if trigger.stage is GuardrailStage.INPUT
                )
            )
            if status is not ExecutionStatus.SUCCESS or output != expected_output:
                raise ValueError(
                    f"guardrail decisions[{index}] input block output is non-canonical"
                )
            if (decision.replacement_response_id, decision.replacement_response_version) != (
                response_id,
                version,
            ):
                raise ValueError(
                    f"guardrail decisions[{index}] input block response version differs"
                )
        elif source is ObservedOutputSource.RESPONSE_BLOCK_RESPONSE:
            response_id, version, expected_output = policy.response_block_response()
            if status is not ExecutionStatus.SUCCESS or output != expected_output:
                raise ValueError(
                    f"guardrail decisions[{index}] response block output is non-canonical"
                )
            response_triggers = tuple(
                trigger
                for trigger in decision.triggered_detectors
                if trigger.stage is GuardrailStage.RESPONSE
            )
            if response_triggers != (response_leak_trigger(),):
                raise ValueError(f"guardrail decisions[{index}] response trigger is non-canonical")
            if (decision.replacement_response_id, decision.replacement_response_version) != (
                response_id,
                version,
            ):
                raise ValueError(f"guardrail decisions[{index}] response block version differs")
        elif source is ObservedOutputSource.UNDERLYING_MODEL:
            if status is not ExecutionStatus.SUCCESS or output is None:
                raise ValueError(
                    f"guardrail decisions[{index}] released output does not match raw run"
                )
            if candidate_sha256(output) != decision.candidate_response_sha256:
                raise ValueError(
                    f"guardrail decisions[{index}] candidate digest does not match raw output"
                )
            response = policy.inspect_response(request, output)
            response_triggers = tuple(
                trigger
                for trigger in decision.triggered_detectors
                if trigger.stage is GuardrailStage.RESPONSE
            )
            if response_triggers != response.triggers:
                raise ValueError(
                    f"guardrail decisions[{index}] response triggers are non-canonical"
                )
        elif status is not ExecutionStatus.ERROR:
            raise ValueError(
                f"guardrail decisions[{index}] execution-error source mismatches raw run"
            )


def write_guardrail_artifact(artifact: GuardrailDecisionArtifact, path: str | Path) -> None:
    """Write a new decision artefact without overwriting."""
    if not isinstance(artifact, GuardrailDecisionArtifact):
        raise TypeError("artifact must be a GuardrailDecisionArtifact")
    serialized = json.dumps(artifact.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized + "\n")


def load_guardrail_artifact(
    path: str | Path, *, raw_run: RunArtifact | None = None
) -> GuardrailDecisionArtifact:
    """Load strict decision evidence and optionally reconcile its raw run."""
    with Path(path).open("r", encoding="utf-8") as source:
        value = json.load(source, object_pairs_hook=_unique_object, parse_constant=_reject_number)
    artifact = GuardrailDecisionArtifact.from_mapping(value)
    if raw_run is not None:
        artifact.validate_against(raw_run)
    return artifact


def _detector_version_mapping(item: DetectorVersion) -> dict[str, JsonValue]:
    return {"id": item.detector_id, "version": item.version, "stage": item.stage.value}


def _trigger_mapping(item: DetectorTrigger) -> dict[str, JsonValue]:
    return {
        "id": item.detector_id,
        "version": item.version,
        "stage": item.stage.value,
        "decision": item.decision.value,
        "explanation": item.explanation,
    }


def _detector_version(value: object) -> DetectorVersion:
    mapping = _mapping(value, "detector")
    _exact_fields(mapping, {"id", "version", "stage"}, "detector")
    return DetectorVersion(
        _non_empty(mapping["id"], "detector.id"),
        _non_empty(mapping["version"], "detector.version"),
        _stage(mapping["stage"]),
    )


def _trigger(value: object) -> DetectorTrigger:
    mapping = _mapping(value, "trigger")
    _exact_fields(mapping, {"id", "version", "stage", "decision", "explanation"}, "trigger")
    return DetectorTrigger(
        detector_id=_non_empty(mapping["id"], "trigger.id"),
        version=_non_empty(mapping["version"], "trigger.version"),
        stage=_stage(mapping["stage"]),
        decision=_decision(mapping["decision"], "trigger.decision"),
        explanation=_non_empty(mapping["explanation"], "trigger.explanation"),
    )


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value


def _array(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an array")
    return value


def _exact_fields(value: Mapping[str, object], fields: set[str], name: str) -> None:
    missing = sorted(fields - value.keys())
    if missing:
        raise ValueError(f"{name} is missing field {missing[0]!r}")
    unknown = sorted(value.keys() - fields)
    if unknown:
        raise ValueError(f"{name} field {unknown[0]!r} is not allowed")


def _non_empty(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")
    return value


def _decision(value: object, name: str) -> GuardrailDecision:
    try:
        return GuardrailDecision(_non_empty(value, name))
    except ValueError as error:
        raise ValueError(f"{name} is unsupported") from error


def _stage(value: object) -> GuardrailStage:
    try:
        return GuardrailStage(_non_empty(value, "stage"))
    except ValueError as error:
        raise ValueError("stage is unsupported") from error


def _output_source(value: object) -> ObservedOutputSource:
    try:
        return ObservedOutputSource(_non_empty(value, "observed_output_source"))
    except ValueError as error:
        raise ValueError("observed_output_source is unsupported") from error


def _sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")
