"""Run a system through runtime guardrails while preserving separate evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from llm_eval_guardrails.guardrail_artifact import (
    GuardrailCaseDecision,
    GuardrailDecisionArtifact,
    ObservedOutputSource,
)
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
    GuardrailDecision,
    NorthstarGuardrailPolicy,
    candidate_sha256,
    final_decision,
)
from llm_eval_guardrails.run_artifact import JsonValue, RunArtifact
from llm_eval_guardrails.runner import run_dataset
from llm_eval_guardrails.system_under_test import SystemRequest, SystemResponse, SystemUnderTest


@dataclass(frozen=True, slots=True)
class _AnonymousDecision:
    triggers: tuple[DetectorTrigger, ...]
    final_decision: GuardrailDecision
    underlying_model_invoked: bool
    candidate_response_released: bool
    candidate_response_replaced: bool
    candidate_response_sha256: str | None
    observed_output_source: ObservedOutputSource
    replacement_response_id: str | None
    replacement_response_version: str | None
    explanation: str


class GuardrailedSystemUnderTest:
    """A request-only wrapper that never receives benchmark case metadata."""

    def __init__(
        self,
        system: SystemUnderTest,
        policy: NorthstarGuardrailPolicy | None = None,
    ) -> None:
        self._system = system
        self._policy = NorthstarGuardrailPolicy() if policy is None else policy
        self._decisions: list[_AnonymousDecision] = []

    @property
    def decisions(self) -> tuple[_AnonymousDecision, ...]:
        return tuple(self._decisions)

    def invoke(self, request: SystemRequest, /) -> SystemResponse:
        """Apply input policy, invoke if allowed, then apply response policy."""
        input_assessment = self._policy.inspect_input(request)
        if input_assessment.decision is GuardrailDecision.BLOCK:
            response_id, version, output = self._policy.input_block_response(
                input_assessment.triggers
            )
            self._decisions.append(
                _AnonymousDecision(
                    triggers=input_assessment.triggers,
                    final_decision=GuardrailDecision.BLOCK,
                    underlying_model_invoked=False,
                    candidate_response_released=False,
                    candidate_response_replaced=False,
                    candidate_response_sha256=None,
                    observed_output_source=ObservedOutputSource.INPUT_BLOCK_RESPONSE,
                    replacement_response_id=response_id,
                    replacement_response_version=version,
                    explanation=INPUT_BLOCK_EXPLANATION,
                )
            )
            return SystemResponse(output)

        try:
            response = self._system.invoke(request)
            if not isinstance(response, SystemResponse):
                raise TypeError(
                    "underlying system returned "
                    f"{type(response).__module__}.{type(response).__qualname__}; "
                    "expected SystemResponse"
                )
            candidate = response.output
            if not isinstance(candidate, str):
                raise TypeError("underlying system response output must be a string")
        except Exception:
            self._decisions.append(
                _AnonymousDecision(
                    triggers=input_assessment.triggers,
                    final_decision=input_assessment.decision,
                    underlying_model_invoked=True,
                    candidate_response_released=False,
                    candidate_response_replaced=False,
                    candidate_response_sha256=None,
                    observed_output_source=ObservedOutputSource.EXECUTION_ERROR,
                    replacement_response_id=None,
                    replacement_response_version=None,
                    explanation=EXECUTION_ERROR_EXPLANATION,
                )
            )
            raise

        response_assessment = self._policy.inspect_response(request, candidate)
        triggers = input_assessment.triggers + response_assessment.triggers
        decision = final_decision(triggers)
        digest = candidate_sha256(candidate)
        if response_assessment.decision is GuardrailDecision.BLOCK:
            response_id, version, output = self._policy.response_block_response()
            self._decisions.append(
                _AnonymousDecision(
                    triggers=triggers,
                    final_decision=decision,
                    underlying_model_invoked=True,
                    candidate_response_released=False,
                    candidate_response_replaced=True,
                    candidate_response_sha256=digest,
                    observed_output_source=ObservedOutputSource.RESPONSE_BLOCK_RESPONSE,
                    replacement_response_id=response_id,
                    replacement_response_version=version,
                    explanation=RESPONSE_BLOCK_EXPLANATION,
                )
            )
            return SystemResponse(output)

        self._decisions.append(
            _AnonymousDecision(
                triggers=triggers,
                final_decision=decision,
                underlying_model_invoked=True,
                candidate_response_released=True,
                candidate_response_replaced=False,
                candidate_response_sha256=digest,
                observed_output_source=ObservedOutputSource.UNDERLYING_MODEL,
                replacement_response_id=None,
                replacement_response_version=None,
                explanation=(
                    WARN_RELEASE_EXPLANATION
                    if decision is GuardrailDecision.WARN
                    else PASS_RELEASE_EXPLANATION
                ),
            )
        )
        return SystemResponse(candidate)


def run_guardrailed_dataset(
    dataset_path: str | Path,
    system: SystemUnderTest,
    *,
    system_id: str,
    system_configuration: Mapping[str, JsonValue] | None = None,
    run_id: str | None = None,
    started_at: datetime | None = None,
) -> tuple[RunArtifact, GuardrailDecisionArtifact]:
    """Return a raw run plus exactly one separate guardrail decision per case."""
    guarded = GuardrailedSystemUnderTest(system)
    raw = run_dataset(
        dataset_path,
        guarded,
        system_id=system_id,
        system_configuration=system_configuration,
        run_id=run_id,
        started_at=started_at,
    )
    if len(guarded.decisions) != len(raw.results):
        raise RuntimeError("guardrail wrapper did not produce exactly one decision per raw result")
    decisions = tuple(
        GuardrailCaseDecision(
            case_id=result.case_id,
            policy_id=GUARDRAIL_POLICY_ID,
            policy_version=GUARDRAIL_POLICY_VERSION,
            detector_versions=DETECTORS,
            triggered_detectors=anonymous.triggers,
            final_decision=anonymous.final_decision,
            underlying_model_invoked=anonymous.underlying_model_invoked,
            candidate_response_released=anonymous.candidate_response_released,
            candidate_response_replaced=anonymous.candidate_response_replaced,
            candidate_response_sha256=anonymous.candidate_response_sha256,
            observed_output_source=anonymous.observed_output_source,
            replacement_response_id=anonymous.replacement_response_id,
            replacement_response_version=anonymous.replacement_response_version,
            explanation=anonymous.explanation,
        )
        for result, anonymous in zip(raw.results, guarded.decisions, strict=True)
    )
    artifact = GuardrailDecisionArtifact(
        run_id=raw.run_id,
        dataset_fingerprint=raw.dataset.fingerprint,
        decisions=decisions,
    )
    artifact.validate_against(raw)
    return raw, artifact
