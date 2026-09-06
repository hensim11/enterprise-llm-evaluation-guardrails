"""Literal deterministic evaluation of stored raw execution evidence."""

from llm_eval_guardrails.case_schema import AssertionType
from llm_eval_guardrails.evaluation_artifact import (
    AssertionEvaluation,
    CaseEvaluationResult,
    EvaluationArtifact,
    EvaluationError,
    EvaluationOutcome,
)
from llm_eval_guardrails.run_artifact import ExecutionStatus, RunArtifact


def evaluate_run(raw_run: RunArtifact) -> EvaluationArtifact:
    """Evaluate all v1 assertions without altering or interpreting raw output."""
    results: list[CaseEvaluationResult] = []
    for case, execution in zip(raw_run.dataset.cases, raw_run.results, strict=True):
        if execution.status is ExecutionStatus.ERROR:
            assert execution.error is not None
            evaluation_error = EvaluationError(
                type="raw_execution_error",
                message=(
                    "deterministic assertions were not evaluated because raw execution "
                    f"failed with {execution.error.type}: {execution.error.message}"
                ),
            )
            assertion_results = tuple(
                AssertionEvaluation(
                    criterion=assertion.criterion,
                    assertion_type=assertion.type,
                    expected=assertion.value,
                    outcome=EvaluationOutcome.ERROR,
                    explanation="not evaluated because raw execution failed",
                )
                for assertion in case.assertions
            )
            results.append(
                CaseEvaluationResult(
                    case_id=case.id,
                    execution_status=execution.status,
                    outcome=EvaluationOutcome.ERROR,
                    assertions=assertion_results,
                    evaluation_error=evaluation_error,
                )
            )
            continue

        assert execution.output is not None
        assertion_results = tuple(
            _evaluate_assertion(
                assertion.type, assertion.criterion, assertion.value, execution.output
            )
            for assertion in case.assertions
        )
        if not assertion_results:
            outcome = EvaluationOutcome.NOT_APPLICABLE
        elif all(result.outcome is EvaluationOutcome.PASS for result in assertion_results):
            outcome = EvaluationOutcome.PASS
        else:
            outcome = EvaluationOutcome.FAIL
        results.append(
            CaseEvaluationResult(
                case_id=case.id,
                execution_status=execution.status,
                outcome=outcome,
                assertions=assertion_results,
                evaluation_error=None,
            )
        )

    artifact = EvaluationArtifact(
        run_id=raw_run.run_id,
        dataset_fingerprint=raw_run.dataset.fingerprint,
        results=tuple(results),
    )
    return artifact


def _evaluate_assertion(
    assertion_type: AssertionType, criterion: str, expected: str, output: str
) -> AssertionEvaluation:
    if assertion_type is AssertionType.EXACT_MATCH:
        passed = output == expected
        explanation = (
            "raw output exactly equals expected value"
            if passed
            else ("raw output does not exactly equal expected value")
        )
    elif assertion_type is AssertionType.CONTAINS:
        passed = expected in output
        explanation = (
            "expected value occurs in raw output"
            if passed
            else ("expected value does not occur in raw output")
        )
    elif assertion_type is AssertionType.NOT_CONTAINS:
        passed = expected not in output
        explanation = (
            "expected value does not occur in raw output"
            if passed
            else ("forbidden expected value occurs in raw output")
        )
    else:  # pragma: no cover - schema v1 prevents unsupported enum members
        raise ValueError(f"unsupported assertion type {assertion_type!r}")
    return AssertionEvaluation(
        criterion=criterion,
        assertion_type=assertion_type,
        expected=expected,
        outcome=EvaluationOutcome.PASS if passed else EvaluationOutcome.FAIL,
        explanation=explanation,
    )
