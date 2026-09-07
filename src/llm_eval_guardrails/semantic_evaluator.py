"""Provider-neutral synchronous semantic evaluation over retained raw evidence."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol, runtime_checkable

from llm_eval_guardrails.evaluation_case import EvaluationCase
from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact
from llm_eval_guardrails.semantic_artifact import (
    JudgeProvenance,
    SemanticCaseResult,
    SemanticEvaluationArtifact,
    SemanticEvaluationError,
    SemanticJudgment,
    SemanticOutcome,
)


@dataclass(frozen=True, slots=True)
class SemanticJudgeRequest:
    """Offline evaluation evidence. It must never be sent to the runtime system."""

    case: EvaluationCase
    observed_response: str

    def __post_init__(self) -> None:
        if not isinstance(self.case, EvaluationCase):
            raise TypeError("case must be EvaluationCase")
        if not isinstance(self.observed_response, str):
            raise TypeError("observed_response must be a string")


@runtime_checkable
class SemanticJudge(Protocol):
    def judge(self, request: SemanticJudgeRequest, /) -> SemanticJudgment: ...


def evaluate_semantically(
    raw_run: RunArtifact,
    judge: SemanticJudge,
    *,
    judge_id: str,
    judge_configuration: dict[str, JsonValue] | None = None,
    case_ids: tuple[str, ...] | None = None,
) -> SemanticEvaluationArtifact:
    """Evaluate a complete run or source-ordered explicit subset, isolating case failures."""
    indices = _selected_indices(raw_run, case_ids)
    results: list[SemanticCaseResult] = []
    for index in indices:
        case = raw_run.dataset.cases[index]
        execution = raw_run.results[index]
        if execution.status is ExecutionStatus.ERROR:
            assert execution.error is not None
            results.append(
                _non_judged_result(
                    case.id,
                    index,
                    execution.status,
                    SemanticOutcome.ERROR,
                    error=SemanticEvaluationError(
                        type="raw_execution_error",
                        message=f"{execution.error.type}: {execution.error.message}",
                    ),
                )
            )
            continue
        if case.expected_behavior is None:
            results.append(
                _non_judged_result(
                    case.id,
                    index,
                    execution.status,
                    SemanticOutcome.NOT_APPLICABLE,
                    rationale="semantic judgement is undefined because expected_behavior is absent",
                )
            )
            continue

        assert execution.output is not None
        started = perf_counter()
        try:
            judgement = judge.judge(SemanticJudgeRequest(case, execution.output))
            if not isinstance(judgement, SemanticJudgment):
                raise TypeError("judge must return SemanticJudgment")
            duration = perf_counter() - started
            result = SemanticCaseResult(
                case_id=case.id,
                raw_result_index=index,
                execution_status=execution.status,
                outcome=judgement.outcome,
                duration_seconds=duration,
                confidence=judgement.confidence,
                rationale=judgement.rationale,
                response_evidence=judgement.response_evidence,
                failure_modes=judgement.failure_modes,
                semantic_error=None,
                usage=judgement.usage,
            )
            for excerpt in result.response_evidence:
                if excerpt not in execution.output:
                    raise ValueError(
                        "judge response evidence is not an exact observed-response substring"
                    )
        except Exception as error:
            duration = perf_counter() - started
            result = SemanticCaseResult(
                case_id=case.id,
                raw_result_index=index,
                execution_status=execution.status,
                outcome=SemanticOutcome.ERROR,
                duration_seconds=duration,
                confidence=None,
                rationale=None,
                response_evidence=(),
                failure_modes=(),
                semantic_error=SemanticEvaluationError(
                    type=f"{type(error).__module__}.{type(error).__qualname__}",
                    message=str(error),
                ),
                usage=None,
            )
        results.append(result)

    artifact = SemanticEvaluationArtifact(
        run_id=raw_run.run_id,
        dataset_fingerprint=raw_run.dataset.fingerprint,
        judge=JudgeProvenance(judge_id, judge_configuration or {}),
        results=tuple(results),
    )
    artifact.validate_against(raw_run)
    return artifact


def _non_judged_result(
    case_id: str,
    index: int,
    status: ExecutionStatus,
    outcome: SemanticOutcome,
    *,
    rationale: str | None = None,
    error: SemanticEvaluationError | None = None,
) -> SemanticCaseResult:
    return SemanticCaseResult(
        case_id=case_id,
        raw_result_index=index,
        execution_status=status,
        outcome=outcome,
        duration_seconds=0.0,
        confidence=None,
        rationale=rationale,
        response_evidence=(),
        failure_modes=(),
        semantic_error=error,
        usage=None,
    )


def _selected_indices(raw_run: RunArtifact, case_ids: tuple[str, ...] | None) -> tuple[int, ...]:
    if case_ids is None:
        return tuple(range(len(raw_run.results)))
    if not isinstance(case_ids, tuple) or not case_ids:
        raise ValueError("case_ids must be a non-empty tuple when supplied")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case_ids must not contain duplicates")
    index_by_id = {case.id: index for index, case in enumerate(raw_run.dataset.cases)}
    unknown = [case_id for case_id in case_ids if case_id not in index_by_id]
    if unknown:
        raise ValueError(f"unknown semantic case ID {unknown[0]!r}")
    indices = tuple(index_by_id[case_id] for case_id in case_ids)
    if tuple(sorted(indices)) != indices:
        raise ValueError("case_ids must preserve raw run ordering")
    return indices
