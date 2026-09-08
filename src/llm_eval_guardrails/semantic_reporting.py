"""Combined reporting with separate execution, deterministic, semantic, and policy fields."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from llm_eval_guardrails.calibration import HumanLabelArtifact
from llm_eval_guardrails.evaluation_artifact import EvaluationArtifact, EvaluationOutcome
from llm_eval_guardrails.guardrail_artifact import GuardrailDecisionArtifact
from llm_eval_guardrails.run_artifact import ExecutionStatus, JsonValue, RunArtifact
from llm_eval_guardrails.semantic_artifact import SemanticEvaluationArtifact, SemanticOutcome

COMBINED_REPORT_SCHEMA_VERSION = "1"


def aggregate_semantic_report(
    raw_run: RunArtifact,
    deterministic: EvaluationArtifact,
    semantic: SemanticEvaluationArtifact,
    *,
    human_labels: HumanLabelArtifact | None = None,
    guardrails: GuardrailDecisionArtifact | None = None,
) -> dict[str, JsonValue]:
    deterministic.validate_against(raw_run)
    semantic.validate_against(raw_run)
    selected_ids = tuple(result.case_id for result in semantic.results)
    if human_labels is not None:
        labelled_ids = tuple(label.case_id for label in human_labels.labels)
        human_labels.validate_against(raw_run, labelled_ids)
        semantic_positions = {case_id: index for index, case_id in enumerate(selected_ids)}
        if any(case_id not in semantic_positions for case_id in labelled_ids):
            raise ValueError("human labels contain a case absent from semantic evidence")
        if tuple(semantic_positions[case_id] for case_id in labelled_ids) != tuple(
            sorted(semantic_positions[case_id] for case_id in labelled_ids)
        ):
            raise ValueError("human labels do not preserve semantic evidence ordering")
    if guardrails is not None:
        guardrails.validate_against(raw_run)
    deterministic_by_id = {result.case_id: result for result in deterministic.results}
    human_by_id = (
        {} if human_labels is None else {item.case_id: item for item in human_labels.labels}
    )
    guardrail_by_id = (
        {} if guardrails is None else {item.case_id: item for item in guardrails.decisions}
    )

    trace: list[JsonValue] = []
    buckets: dict[str, list[tuple[ExecutionStatus, EvaluationOutcome, SemanticOutcome]]] = {}
    trace_buckets: dict[str, list[dict[str, JsonValue]]] = {}
    all_pairs: list[tuple[ExecutionStatus, EvaluationOutcome, SemanticOutcome]] = []
    for result in semantic.results:
        case = raw_run.dataset.cases[result.raw_result_index]
        raw = raw_run.results[result.raw_result_index]
        deterministic_result = deterministic_by_id[result.case_id]
        risk = "uncategorized" if case.risk_category is None else case.risk_category.value
        pair = (raw.status, deterministic_result.outcome, result.outcome)
        all_pairs.append(pair)
        buckets.setdefault(risk, []).append(pair)
        human = human_by_id.get(result.case_id)
        decision = guardrail_by_id.get(result.case_id)
        trace_row: dict[str, JsonValue] = {
            "case_id": result.case_id,
            "risk_category": risk,
            "raw_result_index": result.raw_result_index,
            "execution_status": raw.status.value,
            "execution_error": None if raw.error is None else raw.error.to_mapping(),
            "deterministic_outcome": deterministic_result.outcome.value,
            "semantic_outcome": result.outcome.value,
            "semantic_confidence": None if result.confidence is None else result.confidence.value,
            "semantic_rationale": result.rationale,
            "semantic_evidence": list(result.response_evidence),
            "semantic_failure_modes": [mode.value for mode in result.failure_modes],
            "semantic_error": None
            if result.semantic_error is None
            else result.semantic_error.to_mapping(),
            "human_label": None if human is None else human.label.value,
            "human_rationale": None if human is None else human.rationale,
            "guardrail_decision": None if decision is None else decision.final_decision.value,
        }
        trace.append(trace_row)
        trace_buckets.setdefault(risk, []).append(trace_row)
    overall = _aggregate_pairs(all_pairs)
    _add_optional_component_counts(
        overall, [row for rows in trace_buckets.values() for row in rows]
    )
    by_risk: dict[str, JsonValue] = {}
    for key, value in sorted(buckets.items()):
        aggregate = _aggregate_pairs(value)
        _add_optional_component_counts(aggregate, trace_buckets[key])
        by_risk[key] = aggregate
    return {
        "schema_version": COMBINED_REPORT_SCHEMA_VERSION,
        "source": {
            "run_id": raw_run.run_id,
            "dataset_fingerprint": raw_run.dataset.fingerprint,
            "semantic_judge": semantic.judge.to_mapping(),
            "rubric": {"id": semantic.rubric_id, "version": semantic.rubric_version},
            "prompt_version": semantic.prompt_version,
            "output_schema_version": semantic.output_schema_version,
            "human_labelling_conditions": (
                None
                if human_labels is None
                else {
                    "blinding": human_labels.blinding.value,
                    "disclosures": list(human_labels.disclosures),
                }
            ),
        },
        "limitations": {
            "semantic_measurement_is_nondeterministic": True,
            "semantic_results_are_runtime_enforcement": False,
            "composite_score_produced": False,
        },
        "overall": overall,
        "by_risk_category": by_risk,
        "case_trace": trace,
    }


def _add_optional_component_counts(
    aggregate: dict[str, JsonValue], rows: list[dict[str, JsonValue]]
) -> None:
    human = {"pass": 0, "fail": 0, "unavailable": 0}
    guardrails = {"pass": 0, "warn": 0, "block": 0, "unavailable": 0}
    for row in rows:
        human_value = row["human_label"]
        human["unavailable" if human_value is None else str(human_value)] += 1
        guardrail_value = row["guardrail_decision"]
        guardrails["unavailable" if guardrail_value is None else str(guardrail_value)] += 1
    aggregate["human_labels"] = human
    aggregate["guardrail_decisions"] = guardrails


def _aggregate_pairs(
    pairs: list[tuple[ExecutionStatus, EvaluationOutcome, SemanticOutcome]],
) -> dict[str, JsonValue]:
    execution = {status.value: 0 for status in ExecutionStatus}
    deterministic = {outcome.value: 0 for outcome in EvaluationOutcome}
    semantic = {outcome.value: 0 for outcome in SemanticOutcome}
    for execution_status, deterministic_outcome, semantic_outcome in pairs:
        execution[execution_status.value] += 1
        deterministic[deterministic_outcome.value] += 1
        semantic[semantic_outcome.value] += 1
    judged = semantic["pass"] + semantic["fail"]
    total = len(pairs)
    return {
        "cases": total,
        "execution_statuses": execution,
        "deterministic_outcomes": deterministic,
        "semantic_outcomes": semantic,
        "semantic_pass_rate": {
            "numerator": semantic["pass"],
            "denominator": judged,
            "value": None if judged == 0 else semantic["pass"] / judged,
        },
        "judgement_coverage": {
            "numerator": judged,
            "denominator": total,
            "value": None if total == 0 else judged / total,
        },
    }


def render_semantic_report_markdown(report: Mapping[str, object]) -> str:
    source = _mapping(report["source"], "source")
    overall = _mapping(report["overall"], "overall")
    deterministic = _mapping(overall["deterministic_outcomes"], "deterministic_outcomes")
    semantic = _mapping(overall["semantic_outcomes"], "semantic_outcomes")
    execution = _mapping(overall["execution_statuses"], "execution_statuses")
    human = _mapping(overall["human_labels"], "human_labels")
    guardrails = _mapping(overall["guardrail_decisions"], "guardrail_decisions")
    pass_rate = _mapping(overall["semantic_pass_rate"], "semantic_pass_rate")
    coverage = _mapping(overall["judgement_coverage"], "judgement_coverage")
    trace = report["case_trace"]
    assert isinstance(trace, list)

    def rate(value: object) -> str:
        return "undefined" if value is None else f"{float(value):.1%}"

    deterministic_counts = (
        f"{deterministic['pass']} / {deterministic['fail']} / "
        f"{deterministic['error']} / {deterministic['not_applicable']}"
    )
    semantic_counts = (
        f"{semantic['pass']} / {semantic['fail']} / "
        f"{semantic['error']} / {semantic['not_applicable']}"
    )
    pass_rate_text = (
        f"{pass_rate['numerator']}/{pass_rate['denominator']} ({rate(pass_rate['value'])})"
    )
    coverage_text = f"{coverage['numerator']}/{coverage['denominator']} ({rate(coverage['value'])})"

    lines = [
        "# Combined Deterministic and Semantic Evaluation Report",
        "",
        f"- Run ID: `{source['run_id']}`",
        f"- Dataset fingerprint: `{source['dataset_fingerprint']}`",
        "- Semantic measurements are offline evaluator evidence, not runtime enforcement.",
        "- No composite quality or safety score is produced.",
        "",
        "## Overall components",
        "",
        f"- Raw execution success / error: {execution['success']} / {execution['error']}",
        f"- Deterministic pass / fail / error / N/A: {deterministic_counts}",
        f"- Semantic pass / fail / error / N/A: {semantic_counts}",
        (
            "- Human pass / fail / unavailable: "
            f"{human['pass']} / {human['fail']} / {human['unavailable']}"
        ),
        (
            "- Guardrail pass / warn / block / unavailable: "
            f"{guardrails['pass']} / {guardrails['warn']} / "
            f"{guardrails['block']} / {guardrails['unavailable']}"
        ),
        f"- Semantic pass rate: {pass_rate_text}",
        f"- Judgement coverage: {coverage_text}",
        "",
        "## By risk category",
        "",
        (
            "| Risk | Cases | Raw S/E | Deterministic P/F/E/N | Semantic P/F/E/N | "
            "Human P/F/U | Guardrail P/W/B/U | Pass rate | Coverage |"
        ),
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    by_risk = _mapping(report["by_risk_category"], "by_risk_category")
    for risk, raw_bucket in by_risk.items():
        bucket = _mapping(raw_bucket, "bucket")
        execution_bucket = _mapping(bucket["execution_statuses"], "execution_statuses")
        det = _mapping(bucket["deterministic_outcomes"], "det")
        sem = _mapping(bucket["semantic_outcomes"], "sem")
        human_bucket = _mapping(bucket["human_labels"], "human_labels")
        guardrail_bucket = _mapping(bucket["guardrail_decisions"], "guardrail_decisions")
        pr = _mapping(bucket["semantic_pass_rate"], "pass_rate")
        cov = _mapping(bucket["judgement_coverage"], "coverage")
        lines.append(
            f"| {risk} | {bucket['cases']} | "
            f"{execution_bucket['success']}/{execution_bucket['error']} | "
            f"{det['pass']}/{det['fail']}/{det['error']}/{det['not_applicable']} | "
            f"{sem['pass']}/{sem['fail']}/{sem['error']}/{sem['not_applicable']} | "
            f"{human_bucket['pass']}/{human_bucket['fail']}/{human_bucket['unavailable']} | "
            f"{guardrail_bucket['pass']}/{guardrail_bucket['warn']}/"
            f"{guardrail_bucket['block']}/{guardrail_bucket['unavailable']} | "
            f"{pr['numerator']}/{pr['denominator']} ({rate(pr['value'])}) | "
            f"{cov['numerator']}/{cov['denominator']} ({rate(cov['value'])}) |"
        )
    lines.extend(
        [
            "",
            "## Case trace",
            "",
            "| Case | Raw index | Execution | Deterministic | Semantic | Human | Guardrail |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for raw_row in trace:
        row = _mapping(raw_row, "case_trace[]")
        lines.append(
            f"| `{row['case_id']}` | {row['raw_result_index']} | {row['execution_status']} | "
            f"{row['deterministic_outcome']} | {row['semantic_outcome']} | "
            f"{row['human_label'] or '—'} | {row['guardrail_decision'] or '—'} |"
        )
    return "\n".join(lines) + "\n"


def write_semantic_report(
    report: Mapping[str, object], json_path: Path, markdown_path: Path
) -> None:
    serialized = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    markdown = render_semantic_report_markdown(report)
    with json_path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized)
    with markdown_path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(markdown)


def validate_semantic_report(
    report: Mapping[str, object], json_path: Path, markdown_path: Path
) -> None:
    expected_json = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if json_path.read_text(encoding="utf-8") != expected_json:
        raise ValueError("persisted semantic JSON report does not match canonical rendering")
    if markdown_path.read_text(encoding="utf-8") != render_semantic_report_markdown(report):
        raise ValueError("persisted semantic Markdown report does not match canonical rendering")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value
