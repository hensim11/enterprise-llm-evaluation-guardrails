import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_eval_guardrails import (
    CaseExecutionResult,
    DatasetProvenance,
    EvaluationCase,
    ExecutionError,
    ExecutionStatus,
    FailureMode,
    JudgeConfidence,
    ProviderTokenUsage,
    RunArtifact,
    SemanticCaseResult,
    SemanticEvaluationError,
    SemanticJudgeConfigurationError,
    SemanticJudgment,
    SemanticOutcome,
    SystemProvenance,
    evaluate_semantically,
    load_semantic_artifact,
    write_semantic_artifact,
)


def make_run(
    cases: tuple[EvaluationCase, ...], results: tuple[CaseExecutionResult, ...]
) -> RunArtifact:
    return RunArtifact(
        run_id="semantic-source",
        started_at=datetime(2026, 9, 7, tzinfo=UTC),
        system=SystemProvenance("fixture"),
        dataset=DatasetProvenance("fixture", cases),
        results=results,
    )


def success(case_id: str, output: str = "Safe useful answer.") -> CaseExecutionResult:
    return CaseExecutionResult(case_id, ExecutionStatus.SUCCESS, output, 0.1, None)


class FixedJudge:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def judge(self, request: object) -> object:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    ("judgement", "expected"),
    [
        (
            SemanticJudgment(
                SemanticOutcome.PASS,
                JudgeConfidence.HIGH,
                "It satisfies the expected behaviour.",
                ("Safe useful answer.",),
            ),
            SemanticOutcome.PASS,
        ),
        (
            SemanticJudgment(
                SemanticOutcome.FAIL,
                JudgeConfidence.MEDIUM,
                "It omits the required boundary.",
                ("Safe useful answer.",),
                (FailureMode.OMITTED_REQUIRED_BOUNDARY_OR_HELPFUL_ACTION,),
            ),
            SemanticOutcome.FAIL,
        ),
    ],
)
def test_pass_and_fail_judgements(judgement: SemanticJudgment, expected: SemanticOutcome) -> None:
    case = EvaluationCase(id="one", input="question", expected_behavior="Answer safely.")
    run = make_run((case,), (success("one"),))

    artifact = evaluate_semantically(run, FixedJudge(judgement), judge_id="fake")

    assert artifact.results[0].outcome is expected
    assert artifact.results[0].execution_status is ExecutionStatus.SUCCESS


def test_missing_expectation_is_not_applicable_without_calling_judge() -> None:
    case = EvaluationCase(id="one", input="question")
    judge = FixedJudge(RuntimeError("must not run"))

    result = evaluate_semantically(
        make_run((case,), (success("one"),)), judge, judge_id="fake"
    ).results[0]

    assert result.outcome is SemanticOutcome.NOT_APPLICABLE
    assert judge.calls == 0


def test_raw_execution_error_is_preserved_without_calling_judge() -> None:
    case = EvaluationCase(id="one", input="question", expected_behavior="Answer.")
    execution = CaseExecutionResult(
        "one",
        ExecutionStatus.ERROR,
        None,
        0.1,
        ExecutionError("provider.Error", "failed"),
    )
    judge = FixedJudge(RuntimeError("must not run"))

    result = evaluate_semantically(make_run((case,), (execution,)), judge, judge_id="fake").results[
        0
    ]

    assert result.outcome is SemanticOutcome.ERROR
    assert result.semantic_error.type == "raw_execution_error"
    assert judge.calls == 0


@pytest.mark.parametrize("returned", [RuntimeError("judge failed"), object(), {"outcome": "pass"}])
def test_ordinary_exceptions_and_malformed_return_objects_are_isolated(returned: object) -> None:
    cases = (
        EvaluationCase(id="one", input="one", expected_behavior="Answer."),
        EvaluationCase(id="two", input="two", expected_behavior="Answer."),
    )
    good = SemanticJudgment(SemanticOutcome.PASS, JudgeConfidence.HIGH, "Good.")

    class MixedJudge:
        def __init__(self) -> None:
            self.calls = 0

        def judge(self, request: object) -> object:
            self.calls += 1
            if self.calls == 1:
                if isinstance(returned, Exception):
                    raise returned
                return returned
            return good

    judge = MixedJudge()
    artifact = evaluate_semantically(
        make_run(cases, (success("one"), success("two"))),
        judge,
        judge_id="fake",
    )

    assert [item.outcome for item in artifact.results] == [
        SemanticOutcome.ERROR,
        SemanticOutcome.PASS,
    ]
    assert artifact.results[0].usage is None
    assert judge.calls == 2


def test_run_wide_configuration_failure_stops_after_first_attempted_case() -> None:
    cases = (
        EvaluationCase(id="one", input="one", expected_behavior="Answer."),
        EvaluationCase(id="two", input="two", expected_behavior="Answer."),
    )
    judge = FixedJudge(SemanticJudgeConfigurationError("invalid_json_schema"))

    with pytest.raises(SemanticJudgeConfigurationError, match="invalid_json_schema"):
        evaluate_semantically(
            make_run(cases, (success("one"), success("two"))),
            judge,
            judge_id="fake",
        )

    assert judge.calls == 1


def test_judge_error_cannot_claim_provider_usage() -> None:
    with pytest.raises(ValueError, match="must not contain token usage"):
        SemanticCaseResult(
            case_id="one",
            raw_result_index=0,
            execution_status=ExecutionStatus.SUCCESS,
            outcome=SemanticOutcome.ERROR,
            duration_seconds=0.1,
            confidence=None,
            rationale=None,
            response_evidence=(),
            failure_modes=(),
            semantic_error=SemanticEvaluationError("judge_error", "Malformed response."),
            usage=ProviderTokenUsage(total_tokens=15),
        )


def test_interrupt_is_not_caught() -> None:
    case = EvaluationCase(id="one", input="one", expected_behavior="Answer.")

    class InterruptJudge:
        def judge(self, request: object) -> SemanticJudgment:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        evaluate_semantically(make_run((case,), (success("one"),)), InterruptJudge(), judge_id="x")


def test_fabricated_response_evidence_becomes_explicit_error() -> None:
    case = EvaluationCase(id="one", input="one", expected_behavior="Answer.")
    judgement = SemanticJudgment(
        SemanticOutcome.PASS,
        JudgeConfidence.HIGH,
        "Good.",
        ("fabricated",),
    )

    result = evaluate_semantically(
        make_run((case,), (success("one", "real output"),)),
        FixedJudge(judgement),
        judge_id="fake",
    ).results[0]

    assert result.outcome is SemanticOutcome.ERROR
    assert "substring" in result.semantic_error.message


@pytest.mark.parametrize(
    ("case_ids", "message"),
    [
        (("one", "one"), "duplicates"),
        (("unknown",), "unknown"),
        (("two", "one"), "preserve raw run ordering"),
    ],
)
def test_invalid_explicit_subsets_are_rejected(case_ids: tuple[str, ...], message: str) -> None:
    cases = tuple(
        EvaluationCase(id=value, input=value, expected_behavior="Answer.")
        for value in ("one", "two")
    )
    run = make_run(cases, (success("one"), success("two")))
    judge = FixedJudge(SemanticJudgment(SemanticOutcome.PASS, JudgeConfidence.HIGH, "Good."))

    with pytest.raises(ValueError, match=message):
        evaluate_semantically(run, judge, judge_id="fake", case_ids=case_ids)


def test_partial_source_ordered_subset_round_trips(tmp_path: Path) -> None:
    cases = tuple(
        EvaluationCase(id=value, input=value, expected_behavior="Answer.")
        for value in ("one", "two", "three")
    )
    run = make_run(cases, tuple(success(value) for value in ("one", "two", "three")))
    judge = FixedJudge(SemanticJudgment(SemanticOutcome.PASS, JudgeConfidence.HIGH, "Good."))
    artifact = evaluate_semantically(run, judge, judge_id="fake", case_ids=("one", "three"))
    path = tmp_path / "semantic.json"

    write_semantic_artifact(artifact, path)

    assert load_semantic_artifact(path, raw_run=run).to_mapping() == artifact.to_mapping()


def test_duplicate_semantic_result_is_rejected() -> None:
    case = EvaluationCase(id="one", input="one", expected_behavior="Answer.")
    run = make_run((case,), (success("one"),))
    artifact = evaluate_semantically(
        run,
        FixedJudge(SemanticJudgment(SemanticOutcome.PASS, JudgeConfidence.HIGH, "Good.")),
        judge_id="fake",
    )
    mapping = artifact.to_mapping()
    mapping["results"].append(mapping["results"][0])

    with pytest.raises(ValueError, match="duplicates"):
        type(artifact).from_mapping(mapping)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["source_run"].update(run_id="stale"), "run_id"),
        (
            lambda value: value["source_run"].update(dataset_fingerprint="0" * 64),
            "fingerprint",
        ),
        (lambda value: value["results"][0].update(case_id="unknown"), "case/index"),
        (lambda value: value["results"][0].update(raw_result_index=1), "unknown raw index"),
        (
            lambda value: value["results"][0].update(execution_status="error"),
            "completed semantic result requires successful execution",
        ),
        (lambda value: value.update(extra=True), "not allowed"),
    ],
)
def test_stale_unknown_mismatched_and_unknown_fields_are_rejected(
    mutation: object, message: str
) -> None:
    case = EvaluationCase(id="one", input="one", expected_behavior="Answer.")
    run = make_run((case,), (success("one"),))
    artifact = evaluate_semantically(
        run,
        FixedJudge(SemanticJudgment(SemanticOutcome.PASS, JudgeConfidence.HIGH, "Good.")),
        judge_id="fake",
    )
    mapping = artifact.to_mapping()
    mutation(mapping)

    with pytest.raises((TypeError, ValueError), match=message):
        altered = type(artifact).from_mapping(mapping)
        altered.validate_against(run)


def test_duplicate_json_keys_and_non_finite_numbers_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":"1","schema_version":"1"}', encoding="utf-8")
    nonfinite = tmp_path / "nan.json"
    nonfinite.write_text('{"value":NaN}', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate object key"):
        load_semantic_artifact(duplicate)
    with pytest.raises(ValueError, match="non-standard numeric"):
        load_semantic_artifact(nonfinite)


def test_invalid_judgement_combinations_and_duplicates_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not contain failure"):
        SemanticJudgment(
            SemanticOutcome.PASS,
            JudgeConfidence.HIGH,
            "Good.",
            failure_modes=(FailureMode.UNSUPPORTED_CLAIM,),
        )
    with pytest.raises(ValueError, match="at least one"):
        SemanticJudgment(SemanticOutcome.FAIL, JudgeConfidence.HIGH, "Bad.")
    with pytest.raises(ValueError, match="duplicates"):
        SemanticJudgment(
            SemanticOutcome.FAIL,
            JudgeConfidence.HIGH,
            "Bad.",
            failure_modes=(FailureMode.UNSAFE_COMPLIANCE, FailureMode.UNSAFE_COMPLIANCE),
        )
    with pytest.raises(ValueError, match="duplicates"):
        SemanticJudgment(
            SemanticOutcome.PASS,
            JudgeConfidence.HIGH,
            "Good.",
            response_evidence=("same", "same"),
        )
    invalid_mode = {
        "outcome": "fail",
        "confidence": "high",
        "rationale": "Bad.",
        "response_evidence": [],
        "failure_modes": ["invented"],
    }
    with pytest.raises(ValueError, match="unsupported value"):
        SemanticJudgment.from_mapping(invalid_mode)


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_semantic_artifact(path)
