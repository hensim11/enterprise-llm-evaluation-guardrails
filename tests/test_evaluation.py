import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_eval_guardrails import (
    AssertionType,
    CaseExecutionResult,
    DatasetProvenance,
    EvaluationAssertion,
    EvaluationCase,
    EvaluationOutcome,
    ExecutionError,
    ExecutionStatus,
    RunArtifact,
    SystemProvenance,
    evaluate_run,
    load_evaluation_artifact,
    write_evaluation_artifact,
)


def raw_run(
    cases: tuple[EvaluationCase, ...], results: tuple[CaseExecutionResult, ...]
) -> RunArtifact:
    return RunArtifact(
        run_id="raw-1",
        started_at=datetime(2026, 9, 5, tzinfo=UTC),
        system=SystemProvenance(id="fixture"),
        dataset=DatasetProvenance(source="fixture.jsonl", cases=cases),
        results=results,
    )


def successful(case_id: str, output: str) -> CaseExecutionResult:
    return CaseExecutionResult(
        case_id=case_id,
        status=ExecutionStatus.SUCCESS,
        output=output,
        duration_seconds=0.1,
        error=None,
    )


@pytest.mark.parametrize(
    ("assertion_type", "expected", "output", "outcome"),
    [
        (AssertionType.EXACT_MATCH, " text ", " text ", EvaluationOutcome.PASS),
        (AssertionType.EXACT_MATCH, "text", " text ", EvaluationOutcome.FAIL),
        (AssertionType.CONTAINS, "Case", "Case sensitive", EvaluationOutcome.PASS),
        (AssertionType.CONTAINS, "case", "Case sensitive", EvaluationOutcome.FAIL),
        (AssertionType.NOT_CONTAINS, "secret", "safe output", EvaluationOutcome.PASS),
        (AssertionType.NOT_CONTAINS, "secret", "a secret", EvaluationOutcome.FAIL),
    ],
)
def test_literal_assertion_semantics(
    assertion_type: AssertionType,
    expected: str,
    output: str,
    outcome: EvaluationOutcome,
) -> None:
    case = EvaluationCase(
        id="one",
        input="input",
        assertions=(EvaluationAssertion("criterion", assertion_type, expected),),
    )

    evaluated = evaluate_run(raw_run((case,), (successful("one", output),)))

    assert evaluated.results[0].outcome is outcome
    assert evaluated.results[0].assertions[0].outcome is outcome
    assert evaluated.results[0].assertions[0].expected == expected


def test_empty_output_is_evaluated_and_no_assertions_is_not_applicable() -> None:
    asserted = EvaluationCase(
        id="empty",
        input="input",
        assertions=(EvaluationAssertion("exact-empty-impossible-v1", AssertionType.CONTAINS, "x"),),
    )
    unasserted = EvaluationCase(id="none", input="input")
    run = raw_run(
        (asserted, unasserted),
        (successful("empty", ""), successful("none", "")),
    )

    evaluated = evaluate_run(run)

    assert evaluated.results[0].outcome is EvaluationOutcome.FAIL
    assert evaluated.results[1].outcome is EvaluationOutcome.NOT_APPLICABLE


def test_raw_execution_error_stays_distinct_and_marks_assertions_error() -> None:
    case = EvaluationCase(
        id="error",
        input="input",
        assertions=(EvaluationAssertion("contains", AssertionType.CONTAINS, "x"),),
    )
    execution = CaseExecutionResult(
        case_id="error",
        status=ExecutionStatus.ERROR,
        output=None,
        duration_seconds=0.1,
        error=ExecutionError(type="provider.Error", message="unavailable"),
    )

    evaluated = evaluate_run(raw_run((case,), (execution,)))
    result = evaluated.results[0]

    assert result.execution_status is ExecutionStatus.ERROR
    assert result.outcome is EvaluationOutcome.ERROR
    assert result.assertions[0].outcome is EvaluationOutcome.ERROR
    assert result.evaluation_error is not None
    assert "provider.Error" in result.evaluation_error.message


def test_evaluation_artifact_round_trip_and_exact_raw_join(tmp_path: Path) -> None:
    case = EvaluationCase(id="one", input="input")
    run = raw_run((case,), (successful("one", ""),))
    evaluated = evaluate_run(run)
    path = tmp_path / "evaluated.json"

    write_evaluation_artifact(evaluated, path)
    loaded = load_evaluation_artifact(path, raw_run=run)

    assert loaded.to_mapping() == evaluated.to_mapping()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["source_run"].update(run_id="other"), "run_id does not match"),
        (
            lambda value: value["source_run"].update(dataset_fingerprint="0" * 64),
            "fingerprint does not match",
        ),
        (lambda value: value["results"][0].update(case_id="other"), "case IDs and ordering"),
        (
            lambda value: value["results"][0].update(execution_status="error"),
            "execution error must have evaluation outcome error",
        ),
    ],
)
def test_mismatched_evidence_is_rejected(tmp_path: Path, mutation: object, message: str) -> None:
    case = EvaluationCase(id="one", input="input")
    run = raw_run((case,), (successful("one", ""),))
    value = evaluate_run(run).to_mapping()
    mutation(value)
    path = tmp_path / "mismatch.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_evaluation_artifact(path, raw_run=run)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2", "unsupported evaluation artefact schema version"),
        ("evaluator.version", "2", "unsupported evaluator version"),
    ],
)
def test_unsupported_evaluation_versions_are_rejected(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    case = EvaluationCase(id="one", input="input")
    mapping = evaluate_run(raw_run((case,), (successful("one", ""),))).to_mapping()
    if field == "schema_version":
        mapping[field] = value
    else:
        mapping["evaluator"]["version"] = value
    path = tmp_path / "version.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_evaluation_artifact(path)


def test_duplicate_and_missing_evaluation_results_are_rejected() -> None:
    cases = (EvaluationCase(id="one", input="one"), EvaluationCase(id="two", input="two"))
    run = raw_run(cases, (successful("one", ""), successful("two", "")))
    evaluated = evaluate_run(run)
    duplicate = evaluated.to_mapping()
    duplicate["results"][1]["case_id"] = "one"

    with pytest.raises(ValueError, match="duplicates"):
        type(evaluated).from_mapping(duplicate)

    missing = type(evaluated)(
        run_id=evaluated.run_id,
        dataset_fingerprint=evaluated.dataset_fingerprint,
        results=evaluated.results[:-1],
    )
    with pytest.raises(ValueError, match="case IDs and ordering"):
        missing.validate_against(run)


@pytest.mark.parametrize("field", ["criterion", "assertion_type", "expected"])
def test_tampered_assertion_definition_is_rejected(field: str) -> None:
    case = EvaluationCase(
        id="one",
        input="input",
        assertions=(EvaluationAssertion("original", AssertionType.CONTAINS, "value"),),
    )
    run = raw_run((case,), (successful("one", "value"),))
    evaluated = evaluate_run(run)
    mapping = evaluated.to_mapping()
    mapping["results"][0]["assertions"][0][field] = (
        "not_contains" if field == "assertion_type" else "tampered"
    )
    tampered = type(evaluated).from_mapping(mapping)

    with pytest.raises(ValueError, match="assertions do not match raw case snapshot"):
        tampered.validate_against(run)


def test_non_standard_json_number_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "nan.json"
    path.write_text('{"value":NaN}', encoding="utf-8")

    with pytest.raises(ValueError, match="non-standard numeric constant"):
        load_evaluation_artifact(path)


def test_persisted_failing_outcome_changed_to_pass_is_rejected(tmp_path: Path) -> None:
    case = EvaluationCase(
        id="one",
        input="input",
        assertions=(EvaluationAssertion("forbidden", AssertionType.NOT_CONTAINS, "bad"),),
    )
    run = raw_run((case,), (successful("one", "bad output"),))
    mapping = evaluate_run(run).to_mapping()
    mapping["results"][0]["outcome"] = "pass"
    mapping["results"][0]["assertions"][0]["outcome"] = "pass"
    path = tmp_path / "tampered-pass.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical deterministic recomputation"):
        load_evaluation_artifact(path, raw_run=run)


def test_altered_assertion_evidence_is_rejected_by_recomputation(tmp_path: Path) -> None:
    case = EvaluationCase(
        id="one",
        input="input",
        assertions=(EvaluationAssertion("required", AssertionType.CONTAINS, "good"),),
    )
    run = raw_run((case,), (successful("one", "good output"),))
    mapping = evaluate_run(run).to_mapping()
    mapping["results"][0]["assertions"][0]["explanation"] = "altered evidence"
    path = tmp_path / "tampered-evidence.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical deterministic recomputation"):
        load_evaluation_artifact(path, raw_run=run)


def test_altered_evaluation_error_is_rejected_by_recomputation(tmp_path: Path) -> None:
    case = EvaluationCase(id="error", input="input")
    execution = CaseExecutionResult(
        case_id="error",
        status=ExecutionStatus.ERROR,
        output=None,
        duration_seconds=0.1,
        error=ExecutionError(type="provider.Error", message="unavailable"),
    )
    run = raw_run((case,), (execution,))
    mapping = evaluate_run(run).to_mapping()
    mapping["results"][0]["evaluation_error"]["message"] = "altered error evidence"
    path = tmp_path / "tampered-error.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical deterministic recomputation"):
        load_evaluation_artifact(path, raw_run=run)
