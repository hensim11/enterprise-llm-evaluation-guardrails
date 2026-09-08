#!/usr/bin/env python3
"""Verify every retained Batch A, B, and C evidence bundle without provider calls."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from llm_eval_guardrails import (
    ComparisonEvidencePaths,
    EvidencePathBase,
    EvidenceReference,
    HumanLabelArtifact,
    aggregate_run,
    aggregate_semantic_report,
    calibration_case_ids,
    calibration_report,
    evaluate_run,
    load_calibration_owner_acceptance,
    load_comparison_artifact,
    load_disagreement_review,
    load_evaluation_artifact,
    load_guardrail_artifact,
    load_human_labels,
    load_run_artifact,
    load_semantic_artifact,
    validate_comparison_artifact,
    validate_comparison_markdown,
    validate_json_report,
    validate_markdown_report,
    validate_semantic_report,
    write_calibration_owner_acceptance,
    write_comparison_artifact,
    write_comparison_markdown,
    write_disagreement_review,
    write_evaluation_artifact,
    write_guardrail_artifact,
    write_human_labels,
    write_json_report,
    write_markdown_report,
    write_run_artifact,
    write_semantic_artifact,
    write_semantic_report,
)
from llm_eval_guardrails.calibration import (
    build_blinded_calibration_worksheet,
    build_calibration_worksheet,
    render_calibration_worksheet_markdown,
    validate_calibration_report,
    write_calibration_report,
    write_calibration_worksheet,
)

BASELINE_RELATIVE = Path("evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905")
GUARDRAIL_RELATIVE = Path(
    "evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906"
)
CALIBRATION_INPUT_RELATIVE = Path("evidence/calibration/northstar-v1-guardrailed-batch-c-draft")
BLINDED_TEMPLATE_RELATIVE = Path(
    "evidence/calibration/northstar-v1-guardrailed-batch-c-blinded-template"
)
CALIBRATION_RELATIVE = Path(
    "evidence/calibration/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907"
)
SEMANTIC_RELATIVE = Path(
    "evidence/semantic/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907"
)
_HUMAN_FIELDS_PLACEHOLDER = (
    "**Human label (`pass` or `fail`):** _REQUIRED — blank_\n\n"
    "**Human rationale:** _REQUIRED — blank_"
)
_COMPLETED_HUMAN_FIELDS = re.compile(
    r"^\*\*Human label \(`pass` or `fail`\):\*\* (?P<label>pass|fail)\n\n"
    r"^\*\*Human rationale:\*\* (?P<rationale>[^\n]+)$",
    flags=re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class VerificationSummary:
    """Key evidence-backed counts printed by the repository verifier."""

    baseline_cases: int
    baseline_assertion_passes: int
    baseline_assertions: int
    guardrailed_assertion_passes: int
    guardrailed_assertions: int
    guardrail_passes: int
    guardrail_warnings: int
    guardrail_blocks: int
    avoided_invocations: int
    calibration_agreements: int
    calibration_cases: int
    calibration_disagreements: int
    semantic_passes: int
    semantic_cases: int
    semantic_failures: int
    semantic_coverage: int


def _compare_bytes(generated: Path, retained: Path) -> None:
    if generated.read_bytes() != retained.read_bytes():
        raise ValueError(f"retained derived evidence is stale or altered: {retained}")


def _canonical_copy(writer: object, value: object, retained: Path, generated: Path) -> None:
    writer(value, generated)  # type: ignore[operator]
    _compare_bytes(generated, retained)


def _comparison_paths() -> ComparisonEvidencePaths:
    return ComparisonEvidencePaths(
        EvidenceReference(
            (BASELINE_RELATIVE / "raw-run.json").as_posix(),
            EvidencePathBase.REPOSITORY_ROOT,
        ),
        EvidenceReference(
            (BASELINE_RELATIVE / "evaluated-run.json").as_posix(),
            EvidencePathBase.REPOSITORY_ROOT,
        ),
    )


def _validate_completed_worksheet(
    worksheet: dict[str, object],
    labels: HumanLabelArtifact,
    retained: Path,
    generated: Path,
) -> None:
    retained_text = retained.read_text(encoding="utf-8")
    completed_labels = labels.labels
    parsed_fields = tuple(
        (match.group("label"), match.group("rationale"))
        for match in _COMPLETED_HUMAN_FIELDS.finditer(retained_text)
    )
    if len(parsed_fields) != len(completed_labels):
        raise ValueError(
            f"completed worksheet {retained} must contain exactly "
            f"{len(completed_labels)} strict human label/rationale pairs; "
            f"found {len(parsed_fields)}"
        )
    for position, ((parsed_label, parsed_rationale), expected) in enumerate(
        zip(parsed_fields, completed_labels, strict=True)
    ):
        if (parsed_label, parsed_rationale) != (expected.label.value, expected.rationale):
            raise ValueError(
                f"completed worksheet {retained} human fields at position {position} "
                f"do not match completed label evidence for case {expected.case_id!r}"
            )

    blank_markdown = render_calibration_worksheet_markdown(worksheet)
    sections = blank_markdown.split(_HUMAN_FIELDS_PLACEHOLDER)
    if len(sections) != len(completed_labels) + 1:
        raise ValueError("canonical calibration renderer emitted unexpected human-field structure")
    canonical_parts = [sections[0]]
    for (parsed_label, parsed_rationale), section in zip(parsed_fields, sections[1:], strict=True):
        canonical_parts.extend(
            (
                f"**Human label (`pass` or `fail`):** {parsed_label}\n\n"
                f"**Human rationale:** {parsed_rationale}",
                section,
            )
        )
    generated.write_text("".join(canonical_parts), encoding="utf-8", newline="\n")
    _compare_bytes(generated, retained)


def verify_retained_evidence(repository_root: Path) -> VerificationSummary:
    """Strictly validate and regenerate all retained empirical evidence offline."""
    root = repository_root.resolve()
    baseline_dir = root / BASELINE_RELATIVE
    guardrail_dir = root / GUARDRAIL_RELATIVE
    calibration_input_dir = root / CALIBRATION_INPUT_RELATIVE
    blinded_template_dir = root / BLINDED_TEMPLATE_RELATIVE
    calibration_dir = root / CALIBRATION_RELATIVE
    semantic_dir = root / SEMANTIC_RELATIVE

    with tempfile.TemporaryDirectory(prefix="llm-eval-retained-evidence-") as temp_name:
        generated = Path(temp_name)

        baseline_raw = load_run_artifact(baseline_dir / "raw-run.json")
        baseline_evaluated = load_evaluation_artifact(
            baseline_dir / "evaluated-run.json", raw_run=baseline_raw
        )
        canonical_baseline_evaluated = evaluate_run(baseline_raw)
        _canonical_copy(
            write_run_artifact,
            baseline_raw,
            baseline_dir / "raw-run.json",
            generated / "baseline-raw-run.json",
        )
        _canonical_copy(
            write_evaluation_artifact,
            canonical_baseline_evaluated,
            baseline_dir / "evaluated-run.json",
            generated / "baseline-evaluated-run.json",
        )
        baseline_report = aggregate_run(baseline_raw, baseline_evaluated)
        baseline_summary = generated / "baseline-summary.json"
        baseline_markdown = generated / "baseline-report.md"
        write_json_report(baseline_report, baseline_summary)
        write_markdown_report(baseline_report, baseline_markdown)
        validate_json_report(baseline_report, baseline_dir / "summary.json")
        validate_markdown_report(baseline_report, baseline_dir / "report.md")
        _compare_bytes(baseline_summary, baseline_dir / "summary.json")
        _compare_bytes(baseline_markdown, baseline_dir / "report.md")

        guardrailed_raw = load_run_artifact(guardrail_dir / "raw-run.json")
        guardrailed_evaluated = load_evaluation_artifact(
            guardrail_dir / "evaluated-run.json", raw_run=guardrailed_raw
        )
        decisions = load_guardrail_artifact(
            guardrail_dir / "guardrail-decisions.json", raw_run=guardrailed_raw
        )
        _canonical_copy(
            write_run_artifact,
            guardrailed_raw,
            guardrail_dir / "raw-run.json",
            generated / "guardrailed-raw-run.json",
        )
        _canonical_copy(
            write_evaluation_artifact,
            evaluate_run(guardrailed_raw),
            guardrail_dir / "evaluated-run.json",
            generated / "guardrailed-evaluated-run.json",
        )
        _canonical_copy(
            write_guardrail_artifact,
            decisions,
            guardrail_dir / "guardrail-decisions.json",
            generated / "guardrail-decisions.json",
        )
        guardrailed_report = aggregate_run(guardrailed_raw, guardrailed_evaluated)
        guardrailed_summary = generated / "guardrailed-summary.json"
        guardrailed_markdown = generated / "guardrailed-report.md"
        write_json_report(guardrailed_report, guardrailed_summary)
        write_markdown_report(guardrailed_report, guardrailed_markdown)
        validate_json_report(guardrailed_report, guardrail_dir / "summary.json")
        validate_markdown_report(guardrailed_report, guardrail_dir / "report.md")
        _compare_bytes(guardrailed_summary, guardrail_dir / "summary.json")
        _compare_bytes(guardrailed_markdown, guardrail_dir / "report.md")

        paths = _comparison_paths()
        comparison = load_comparison_artifact(
            guardrail_dir / "comparison.json",
            baseline_raw=baseline_raw,
            baseline_evaluated=baseline_evaluated,
            guardrailed_raw=guardrailed_raw,
            guardrailed_evaluated=guardrailed_evaluated,
            guardrail_decisions=decisions,
            evidence_paths=paths,
        )
        comparison_json = generated / "comparison.json"
        comparison_markdown = generated / "comparison.md"
        write_comparison_artifact(comparison, comparison_json)
        write_comparison_markdown(comparison, comparison_markdown)
        validate_comparison_artifact(comparison, guardrail_dir / "comparison.json")
        validate_comparison_markdown(comparison, guardrail_dir / "comparison.md")
        _compare_bytes(comparison_json, guardrail_dir / "comparison.json")
        _compare_bytes(comparison_markdown, guardrail_dir / "comparison.md")

        selected_ids = calibration_case_ids(guardrailed_raw, guardrailed_evaluated)
        input_labels = load_human_labels(
            calibration_input_dir / "human-labels.completed.json",
            raw_run=guardrailed_raw,
            case_ids=selected_ids,
        )
        labels = load_human_labels(
            calibration_dir / "human-labels.completed.json",
            raw_run=guardrailed_raw,
            case_ids=selected_ids,
        )
        if input_labels != labels:
            raise ValueError("retained calibration human-label copies do not match")
        _canonical_copy(
            write_human_labels,
            labels,
            calibration_dir / "human-labels.completed.json",
            generated / "human-labels.completed.json",
        )
        _compare_bytes(
            calibration_input_dir / "human-labels.completed.json",
            calibration_dir / "human-labels.completed.json",
        )

        unblinded = build_calibration_worksheet(guardrailed_raw, guardrailed_evaluated)
        unblinded_json = generated / "human-labels.draft.json"
        unblinded_blank_markdown = generated / "human-labels.blank.md"
        write_calibration_worksheet(unblinded, unblinded_json, unblinded_blank_markdown)
        _compare_bytes(unblinded_json, calibration_input_dir / "human-labels.draft.json")
        _validate_completed_worksheet(
            unblinded,
            labels,
            calibration_input_dir / "human-labels.draft.md",
            generated / "human-labels.completed.md",
        )

        blinded = build_blinded_calibration_worksheet(guardrailed_raw, guardrailed_evaluated)
        blinded_json = generated / "blinded-human-labels.draft.json"
        blinded_markdown = generated / "blinded-human-labels.draft.md"
        write_calibration_worksheet(blinded, blinded_json, blinded_markdown)
        _compare_bytes(blinded_json, blinded_template_dir / "human-labels.draft.json")
        _compare_bytes(blinded_markdown, blinded_template_dir / "human-labels.draft.md")

        calibration_semantic = load_semantic_artifact(
            calibration_dir / "semantic-evaluation.json", raw_run=guardrailed_raw
        )
        _canonical_copy(
            write_semantic_artifact,
            calibration_semantic,
            calibration_dir / "semantic-evaluation.json",
            generated / "calibration-semantic-evaluation.json",
        )
        disagreement = load_disagreement_review(
            calibration_dir / "disagreement-review.completed.json",
            raw_run=guardrailed_raw,
            semantic=calibration_semantic,
            human=labels,
        )
        _canonical_copy(
            write_disagreement_review,
            disagreement,
            calibration_dir / "disagreement-review.completed.json",
            generated / "disagreement-review.completed.json",
        )
        canonical_calibration = calibration_report(
            guardrailed_raw,
            guardrailed_evaluated,
            calibration_semantic,
            labels,
            disagreement,
        )
        calibration_json = generated / "calibration.json"
        calibration_markdown = generated / "calibration.md"
        write_calibration_report(canonical_calibration, calibration_json, calibration_markdown)
        validate_calibration_report(
            canonical_calibration,
            calibration_dir / "calibration.json",
            calibration_dir / "calibration.md",
        )
        _compare_bytes(calibration_json, calibration_dir / "calibration.json")
        _compare_bytes(calibration_markdown, calibration_dir / "calibration.md")
        acceptance = load_calibration_owner_acceptance(
            calibration_dir / "owner-acceptance.json",
            raw_run=guardrailed_raw,
            deterministic=guardrailed_evaluated,
            semantic=calibration_semantic,
            human=labels,
            disagreement_review=disagreement,
            reviewed_calibration_report=canonical_calibration,
        )
        _canonical_copy(
            write_calibration_owner_acceptance,
            acceptance,
            calibration_dir / "owner-acceptance.json",
            generated / "owner-acceptance.json",
        )

        semantic = load_semantic_artifact(
            semantic_dir / "semantic-evaluation.json", raw_run=guardrailed_raw
        )
        _canonical_copy(
            write_semantic_artifact,
            semantic,
            semantic_dir / "semantic-evaluation.json",
            generated / "semantic-evaluation.json",
        )
        semantic_report = aggregate_semantic_report(
            guardrailed_raw,
            guardrailed_evaluated,
            semantic,
            human_labels=labels,
            guardrails=decisions,
        )
        semantic_json = generated / "semantic-summary.json"
        semantic_markdown = generated / "semantic-report.md"
        write_semantic_report(semantic_report, semantic_json, semantic_markdown)
        validate_semantic_report(
            semantic_report,
            semantic_dir / "semantic-summary.json",
            semantic_dir / "semantic-report.md",
        )
        _compare_bytes(semantic_json, semantic_dir / "semantic-summary.json")
        _compare_bytes(semantic_markdown, semantic_dir / "semantic-report.md")

    baseline_counts = baseline_report.to_mapping()["overall"]
    guardrailed_counts = guardrailed_report.to_mapping()["overall"]
    comparison_counts = comparison.to_mapping()["guardrails"]
    calibration_counts = canonical_calibration["counts"]
    semantic_counts = semantic_report["overall"]
    return VerificationSummary(
        baseline_cases=baseline_counts["total_cases"],
        baseline_assertion_passes=baseline_counts["assertions"]["pass"],
        baseline_assertions=baseline_counts["assertions"]["expected"],
        guardrailed_assertion_passes=guardrailed_counts["assertions"]["pass"],
        guardrailed_assertions=guardrailed_counts["assertions"]["expected"],
        guardrail_passes=comparison_counts["decision_counts"]["pass"],
        guardrail_warnings=comparison_counts["decision_counts"]["warn"],
        guardrail_blocks=comparison_counts["decision_counts"]["block"],
        avoided_invocations=comparison_counts["underlying_model_invocations_avoided"],
        calibration_agreements=calibration_counts["agreement"],
        calibration_cases=calibration_counts["selected_cases"],
        calibration_disagreements=calibration_counts["disagreement"],
        semantic_passes=semantic_counts["semantic_outcomes"]["pass"],
        semantic_cases=semantic_counts["cases"],
        semantic_failures=semantic_counts["semantic_outcomes"]["fail"],
        semantic_coverage=semantic_counts["judgement_coverage"]["numerator"],
    )


def _print_summary(summary: VerificationSummary) -> None:
    print("Retained evidence verification succeeded (offline; no provider calls).")
    print(
        "Batch A baseline: "
        f"{summary.baseline_cases} cases; "
        f"{summary.baseline_assertion_passes}/{summary.baseline_assertions} literal assertions."
    )
    print(
        "Batch B guardrailed comparison: "
        f"{summary.guardrailed_assertion_passes}/{summary.guardrailed_assertions} literal "
        f"assertions; decisions {summary.guardrail_passes} PASS / "
        f"{summary.guardrail_warnings} WARN / {summary.guardrail_blocks} BLOCK; "
        f"{summary.avoided_invocations} invocations avoided."
    )
    print(
        "Batch C calibration: "
        f"{summary.calibration_agreements}/{summary.calibration_cases} exact agreement; "
        f"{summary.calibration_disagreements} reviewed disagreements; owner acceptance valid."
    )
    print(
        "Batch C semantic: "
        f"{summary.semantic_passes}/{summary.semantic_cases} pass; "
        f"{summary.semantic_failures} fail; "
        f"{summary.semantic_coverage}/{summary.semantic_cases} judgement coverage."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and canonically regenerate all retained Batch A-C evidence."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root containing the retained evidence tree",
    )
    args = parser.parse_args(argv)
    try:
        summary = verify_retained_evidence(args.repository_root)
    except (OSError, TypeError, ValueError) as error:
        print(f"Retained evidence verification FAILED: {error}", file=sys.stderr)
        return 1
    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
