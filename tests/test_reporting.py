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
    ExecutionError,
    ExecutionStatus,
    RiskCategory,
    RunArtifact,
    SystemProvenance,
    aggregate_run,
    evaluate_run,
    render_markdown_report,
    validate_json_report,
    validate_markdown_report,
    write_json_report,
    write_markdown_report,
)


def test_aggregate_reconciles_counts_categories_coverage_and_markdown() -> None:
    cases = (
        EvaluationCase(
            id="pass",
            input="input",
            risk_category=RiskCategory.PRIVACY,
            assertions=(EvaluationAssertion("yes", AssertionType.CONTAINS, "yes"),),
        ),
        EvaluationCase(
            id="fail",
            input="input",
            risk_category=RiskCategory.PRIVACY,
            assertions=(EvaluationAssertion("no", AssertionType.NOT_CONTAINS, "no"),),
        ),
        EvaluationCase(
            id="error",
            input="input",
            assertions=(EvaluationAssertion("x", AssertionType.CONTAINS, "x"),),
        ),
        EvaluationCase(id="n-a", input="input"),
    )
    results = (
        CaseExecutionResult("pass", ExecutionStatus.SUCCESS, "yes", 0.1, None),
        CaseExecutionResult("fail", ExecutionStatus.SUCCESS, "no", 0.1, None),
        CaseExecutionResult(
            "error",
            ExecutionStatus.ERROR,
            None,
            0.1,
            ExecutionError("provider.Error", "failed"),
        ),
        CaseExecutionResult("n-a", ExecutionStatus.SUCCESS, "anything", 0.1, None),
    )
    raw = RunArtifact(
        run_id="report-run",
        started_at=datetime(2026, 9, 5, tzinfo=UTC),
        system=SystemProvenance("fixture"),
        dataset=DatasetProvenance("fixture.jsonl", cases),
        results=results,
    )
    report = aggregate_run(raw, evaluate_run(raw))
    mapping = report.to_mapping()
    overall = mapping["overall"]

    assert overall["total_cases"] == 4
    assert overall["execution"] == {"success": 3, "error": 1}
    assert overall["case_outcomes"] == {
        "pass": 1,
        "fail": 1,
        "error": 1,
        "not_applicable": 1,
    }
    assert overall["assertions"] == {"expected": 3, "pass": 1, "fail": 1, "error": 1}
    assert overall["assertion_pass_rate"] == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert overall["assertion_evaluation_coverage"]["value"] == 2 / 3
    assert overall["deterministic_case_coverage"]["value"] == 0.5
    assert mapping["by_risk_category"]["privacy"]["total_cases"] == 2
    assert mapping["by_risk_category"]["uncategorized"]["total_cases"] == 2
    assert len(mapping["case_traceability"]) == 4

    markdown = render_markdown_report(report)
    assert "1/2 (50.0%)" in markdown
    assert "2/3 (66.7%)" in markdown
    assert "| privacy | 2 |" in markdown
    assert "| error | uncategorized | 2 | 2 | error | error | 1 |" in markdown
    assert json.loads(json.dumps(mapping))["overall"]["assertions"]["pass"] == 1


def test_zero_denominators_are_explicitly_undefined() -> None:
    case = EvaluationCase(id="none", input="input")
    raw = RunArtifact(
        run_id="zero",
        started_at=datetime(2026, 9, 5, tzinfo=UTC),
        system=SystemProvenance("fixture"),
        dataset=DatasetProvenance("fixture.jsonl", (case,)),
        results=(CaseExecutionResult("none", ExecutionStatus.SUCCESS, "", 0.1, None),),
    )
    report = aggregate_run(raw, evaluate_run(raw))

    assert report.to_mapping()["overall"]["assertion_pass_rate"] == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    assert "0/0 (undefined)" in render_markdown_report(report)


def test_persisted_reports_must_match_canonical_aggregate(
    tmp_path: Path,
) -> None:
    case = EvaluationCase(
        id="one",
        input="input",
        assertions=(EvaluationAssertion("required", AssertionType.CONTAINS, "yes"),),
    )
    raw = RunArtifact(
        run_id="report-validation",
        started_at=datetime(2026, 9, 5, tzinfo=UTC),
        system=SystemProvenance("fixture"),
        dataset=DatasetProvenance("fixture.jsonl", (case,)),
        results=(CaseExecutionResult("one", ExecutionStatus.SUCCESS, "yes", 0.1, None),),
    )
    report = aggregate_run(raw, evaluate_run(raw))
    json_path = tmp_path / "summary.json"
    markdown_path = tmp_path / "report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, markdown_path)

    validate_json_report(report, json_path)
    validate_markdown_report(report, markdown_path)

    value = json.loads(json_path.read_text(encoding="utf-8"))
    value["overall"]["assertions"]["pass"] = 0
    json_path.write_text(json.dumps(value), encoding="utf-8")
    markdown_path.write_text(
        markdown_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="canonical aggregate recomputation"):
        validate_json_report(report, json_path)
    with pytest.raises(ValueError, match="canonical aggregate rendering"):
        validate_markdown_report(report, markdown_path)
