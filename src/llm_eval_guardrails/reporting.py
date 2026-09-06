"""Reconciled aggregation and JSON/Markdown rendering from one result model."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from llm_eval_guardrails.evaluation_artifact import EvaluationArtifact, EvaluationOutcome
from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact

SUMMARY_SCHEMA_VERSION = "1"
UNCATEGORIZED = "uncategorized"


@dataclass(frozen=True, slots=True)
class AggregateReport:
    """Validated aggregate whose mapping feeds both serialized report formats."""

    raw_run: RunArtifact
    evaluated_run: EvaluationArtifact
    raw_evidence_path: str
    evaluated_evidence_path: str

    def __post_init__(self) -> None:
        self.evaluated_run.validate_against(self.raw_run)
        if not isinstance(self.raw_evidence_path, str) or not self.raw_evidence_path:
            raise ValueError("raw_evidence_path must be a non-empty string")
        if not isinstance(self.evaluated_evidence_path, str) or not self.evaluated_evidence_path:
            raise ValueError("evaluated_evidence_path must be a non-empty string")

    def to_mapping(self) -> dict[str, JsonValue]:
        cases = list(
            zip(
                self.raw_run.dataset.cases,
                self.raw_run.results,
                self.evaluated_run.results,
                strict=True,
            )
        )
        overall = _counts(cases)
        category_names = sorted(
            {
                case.risk_category.value if case.risk_category is not None else UNCATEGORIZED
                for case, _, _ in cases
            }
            | {UNCATEGORIZED}
        )
        by_category: dict[str, JsonValue] = {}
        for category in category_names:
            subset = [
                item
                for item in cases
                if (
                    item[0].risk_category.value
                    if item[0].risk_category is not None
                    else UNCATEGORIZED
                )
                == category
            ]
            by_category[category] = _counts(subset)

        traces: list[JsonValue] = []
        for index, (case, execution, evaluated) in enumerate(cases):
            traces.append(
                {
                    "case_id": case.id,
                    "risk_category": (
                        case.risk_category.value
                        if case.risk_category is not None
                        else UNCATEGORIZED
                    ),
                    "raw_result_index": index,
                    "evaluated_result_index": index,
                    "execution_status": execution.status.value,
                    "case_outcome": evaluated.outcome.value,
                    "expected_assertions": len(case.assertions),
                }
            )

        return {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "source": {
                "run_id": self.raw_run.run_id,
                "dataset_fingerprint": self.raw_run.dataset.fingerprint,
                "raw_evidence": self.raw_evidence_path,
                "evaluated_evidence": self.evaluated_evidence_path,
            },
            "overall": overall,
            "by_risk_category": by_category,
            "case_traceability": traces,
        }


def aggregate_run(
    raw_run: RunArtifact,
    evaluated_run: EvaluationArtifact,
    *,
    raw_evidence_path: str = "raw-run.json",
    evaluated_evidence_path: str = "evaluated-run.json",
) -> AggregateReport:
    """Create a validated aggregate over exactly matching case evidence."""
    return AggregateReport(
        raw_run=raw_run,
        evaluated_run=evaluated_run,
        raw_evidence_path=raw_evidence_path,
        evaluated_evidence_path=evaluated_evidence_path,
    )


def write_json_report(report: AggregateReport, path: str | Path) -> None:
    """Write the aggregate mapping as a new JSON file."""
    serialized = json.dumps(report.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized + "\n")


def validate_json_report(report: AggregateReport, path: str | Path) -> None:
    """Require a persisted JSON summary to equal the canonical aggregate exactly."""
    with Path(path).open("r", encoding="utf-8") as source:
        value = json.load(
            source,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_non_standard_number,
        )
    if value != report.to_mapping():
        raise ValueError("JSON summary does not match canonical aggregate recomputation")


def render_markdown_report(report: AggregateReport) -> str:
    """Render human-readable results exclusively from the shared aggregate mapping."""
    value = report.to_mapping()
    source = value["source"]
    overall = value["overall"]
    executions = overall["execution"]
    cases = overall["case_outcomes"]
    assertions = overall["assertions"]
    pass_rate = overall["assertion_pass_rate"]
    assertion_coverage = overall["assertion_evaluation_coverage"]
    case_coverage = overall["deterministic_case_coverage"]

    lines = [
        "# Deterministic Evaluation Report",
        "",
        f"- Run ID: `{_md(source['run_id'])}`",
        f"- Dataset fingerprint: `{_md(source['dataset_fingerprint'])}`",
        f"- Raw evidence: `{_md(source['raw_evidence'])}`",
        f"- Evaluated evidence: `{_md(source['evaluated_evidence'])}`",
        "",
        "## Overall counts",
        "",
        f"- Total cases: {overall['total_cases']}",
        f"- Execution successes / errors: {executions['success']} / {executions['error']}",
        (
            "- Case outcomes (pass / fail / error / not applicable): "
            f"{cases['pass']} / {cases['fail']} / {cases['error']} / "
            f"{cases['not_applicable']}"
        ),
        f"- Total expected assertions: {assertions['expected']}",
        (
            "- Assertion outcomes (pass / fail / error): "
            f"{assertions['pass']} / {assertions['fail']} / {assertions['error']}"
        ),
        f"- Cases with no applicable deterministic assertions: {overall['not_applicable_cases']}",
        (f"- Assertion pass rate (passed / evaluated, errors excluded): {_rate_text(pass_rate)}"),
        (
            "- Assertion evaluation coverage (evaluated / expected): "
            f"{_rate_text(assertion_coverage)}"
        ),
        (f"- Deterministic case coverage (pass-or-fail / all cases): {_rate_text(case_coverage)}"),
        "",
        "An execution error is not an assertion failure. Non-applicable cases and assertion "
        "errors are excluded from the pass-rate denominator and remain visible in coverage.",
        "",
        "## Results by risk category",
        "",
        (
            "| Risk category | Cases | Exec errors | Pass | Fail | Error | N/A | "
            "Assertions P/F/E | Pass rate | Coverage |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, category_counts in value["by_risk_category"].items():
        outcomes = category_counts["case_outcomes"]
        assertion_counts = category_counts["assertions"]
        lines.append(
            f"| {_md(category)} | {category_counts['total_cases']} | "
            f"{category_counts['execution']['error']} | {outcomes['pass']} | "
            f"{outcomes['fail']} | {outcomes['error']} | {outcomes['not_applicable']} | "
            f"{assertion_counts['pass']}/{assertion_counts['fail']}/{assertion_counts['error']} | "
            f"{_rate_text(category_counts['assertion_pass_rate'])} | "
            f"{_rate_text(category_counts['assertion_evaluation_coverage'])} |"
        )

    lines.extend(
        [
            "",
            "## Case traceability",
            "",
            "Indices are zero-based positions in the named raw and evaluated evidence files.",
            "",
            (
                "| Case ID | Risk category | Raw index | Evaluated index | Execution | "
                "Outcome | Expected assertions |"
            ),
            "| --- | --- | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for trace in value["case_traceability"]:
        lines.append(
            f"| {_md(trace['case_id'])} | {_md(trace['risk_category'])} | "
            f"{trace['raw_result_index']} | {trace['evaluated_result_index']} | "
            f"{trace['execution_status']} | {trace['case_outcome']} | "
            f"{trace['expected_assertions']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "These metrics measure only literal, case-sensitive string assertions. They do "
            "not establish semantic correctness, groundedness, safety, privacy, injection "
            "resistance, or a policy decision. Baseline prompt instructions are part of the "
            "system under test and are not runtime guardrails.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(report: AggregateReport, path: str | Path) -> None:
    """Write a human-readable rendering to a new file."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(render_markdown_report(report))


def validate_markdown_report(report: AggregateReport, path: str | Path) -> None:
    """Require persisted Markdown to equal a fresh canonical rendering exactly."""
    persisted = Path(path).read_text(encoding="utf-8")
    if persisted != render_markdown_report(report):
        raise ValueError("Markdown report does not match canonical aggregate rendering")


def _counts(items: list[tuple[object, object, object]]) -> dict[str, JsonValue]:
    execution_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()
    assertion_counts: Counter[str] = Counter()
    expected_assertions = 0
    for case, execution, evaluated in items:
        execution_counts[execution.status.value] += 1
        case_counts[evaluated.outcome.value] += 1
        expected_assertions += len(case.assertions)
        assertion_counts.update(item.outcome.value for item in evaluated.assertions)

    evaluated_assertions = assertion_counts["pass"] + assertion_counts["fail"]
    deterministically_evaluated_cases = case_counts["pass"] + case_counts["fail"]
    return {
        "total_cases": len(items),
        "execution": {
            "success": execution_counts[ExecutionStatus.SUCCESS.value],
            "error": execution_counts[ExecutionStatus.ERROR.value],
        },
        "case_outcomes": {
            outcome.value: case_counts[outcome.value] for outcome in EvaluationOutcome
        },
        "assertions": {
            "expected": expected_assertions,
            "pass": assertion_counts[EvaluationOutcome.PASS.value],
            "fail": assertion_counts[EvaluationOutcome.FAIL.value],
            "error": assertion_counts[EvaluationOutcome.ERROR.value],
        },
        "not_applicable_cases": case_counts[EvaluationOutcome.NOT_APPLICABLE.value],
        "assertion_pass_rate": _rate(assertion_counts["pass"], evaluated_assertions),
        "assertion_evaluation_coverage": _rate(evaluated_assertions, expected_assertions),
        "deterministic_case_coverage": _rate(deterministically_evaluated_cases, len(items)),
    }


def _rate(numerator: int, denominator: int) -> dict[str, JsonValue]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if denominator == 0 else numerator / denominator,
    }


def _rate_text(rate: Mapping[str, JsonValue]) -> str:
    value = rate["value"]
    if value is None:
        return f"{rate['numerator']}/{rate['denominator']} (undefined)"
    return f"{rate['numerator']}/{rate['denominator']} ({float(value):.1%})"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("`", "\\`")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")
