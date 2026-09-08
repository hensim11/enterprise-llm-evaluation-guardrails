import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from llm_eval_guardrails import (
    CalibrationOwnerAcceptance,
    CaseExecutionResult,
    DatasetProvenance,
    DisagreementClassification,
    DisagreementReviewArtifact,
    EvaluationCase,
    ExecutionError,
    ExecutionStatus,
    FailureMode,
    HumanCaseLabel,
    HumanLabel,
    HumanLabelArtifact,
    JudgeConfidence,
    JudgeProvenance,
    LabelBlinding,
    RunArtifact,
    SemanticCaseResult,
    SemanticEvaluationArtifact,
    SemanticEvaluationError,
    SemanticOutcome,
    SystemProvenance,
    aggregate_semantic_report,
    build_blinded_calibration_worksheet,
    build_calibration_owner_acceptance,
    build_calibration_worksheet,
    build_disagreement_review_template,
    calibration_case_ids,
    evaluate_run,
    load_calibration_owner_acceptance,
    load_evaluation_artifact,
    load_human_labels,
    load_run_artifact,
    load_semantic_artifact,
    render_semantic_report_markdown,
    write_calibration_owner_acceptance,
)
from llm_eval_guardrails.calibration import (
    calibration_report,
    load_disagreement_review,
    render_calibration_report_markdown,
    render_calibration_worksheet_markdown,
    render_disagreement_review_markdown,
    validate_calibration_report,
    write_calibration_report,
    write_disagreement_review,
)
from llm_eval_guardrails.semantic_reporting import (
    validate_semantic_report,
    write_semantic_report,
)

RETAINED = Path("evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906")
COMPLETED_LABELS = Path(
    "evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json"
)
BLINDED_TEMPLATE = Path("evidence/calibration/northstar-v1-guardrailed-batch-c-blinded-template")
RETAINED_CALIBRATION = Path(
    "evidence/calibration/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907"
)


def test_fixed_selection_has_required_anchors_and_prelabelled_rule() -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)

    selected = calibration_case_ids(raw, deterministic)
    worksheet = build_calibration_worksheet(raw, deterministic)

    assert len(selected) == 12
    assert tuple(worksheet["selection"]["case_ids"]) == selected
    assert [item["raw_result_index"] for item in worksheet["cases"]] == sorted(
        item["raw_result_index"] for item in worksheet["cases"]
    )
    assert (
        sum(item["deterministic_outcome"] == "not_applicable" for item in worksheet["cases"]) == 5
    )
    assert sum(item["deterministic_outcome"] == "fail" for item in worksheet["cases"]) == 3
    assert all(item["human_label"] is None for item in worksheet["cases"])
    assert worksheet["selection"]["challenge_weighted"] is True
    markdown = render_calibration_worksheet_markdown(worksheet)
    assert "DRAFT / INCOMPLETE" in markdown
    assert "not representative" in markdown
    for item in worksheet["cases"]:
        assert item["input"] in markdown
        assert item["expected_behavior"] in markdown
        assert item["observed_response"] in markdown


def test_future_blinded_worksheet_omits_outcomes_and_selection_reasons() -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)

    worksheet = build_blinded_calibration_worksheet(raw, deterministic)
    markdown = render_calibration_worksheet_markdown(worksheet)

    assert worksheet["labelling_conditions"]["blinding"].startswith("blinded_to_")
    assert all("deterministic_outcome" not in item for item in worksheet["cases"])
    assert all("selection_reason" not in item for item in worksheet["cases"])
    assert "- Selection:" not in markdown
    assert "- Deterministic outcome:" not in markdown
    assert "BLINDED DRAFT" in markdown


def test_retained_future_blinded_template_is_canonical_and_contains_no_labels() -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)
    expected = build_blinded_calibration_worksheet(raw, deterministic)
    retained_json = json.loads((BLINDED_TEMPLATE / "human-labels.draft.json").read_text())
    retained_markdown = (BLINDED_TEMPLATE / "human-labels.draft.md").read_text()

    assert retained_json == expected
    assert retained_markdown == render_calibration_worksheet_markdown(expected)
    assert all(item["human_label"] is None for item in retained_json["cases"])
    assert all(item["human_rationale"] is None for item in retained_json["cases"])
    assert len(re.findall(r"Human label .*_REQUIRED — blank_", retained_markdown)) == 12
    assert len(re.findall(r"Human rationale:.*_REQUIRED — blank_", retained_markdown)) == 12
    completed = load_human_labels(
        COMPLETED_LABELS,
        raw_run=raw,
        case_ids=calibration_case_ids(raw, deterministic),
    )
    assert all(label.rationale not in retained_markdown for label in completed.labels)


def test_completed_owner_labels_validate_exactly_and_record_partial_unblinding() -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)

    labels = load_human_labels(
        COMPLETED_LABELS,
        raw_run=raw,
        case_ids=calibration_case_ids(raw, deterministic),
    )

    assert len(labels.labels) == 12
    assert labels.run_id == raw.run_id
    assert labels.dataset_fingerprint == raw.dataset.fingerprint
    assert tuple(item.case_id for item in labels.labels) == calibration_case_ids(raw, deterministic)
    assert tuple(item.raw_result_index for item in labels.labels) == (
        5,
        8,
        14,
        16,
        19,
        20,
        21,
        22,
        26,
        27,
        28,
        31,
    )
    assert tuple(item.label.value for item in labels.labels) == (
        "pass",
        "pass",
        "fail",
        "fail",
        "fail",
        "fail",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
        "pass",
    )
    assert all(item.rationale.strip() for item in labels.labels)
    assert sum(item.label is HumanLabel.PASS for item in labels.labels) == 8
    assert sum(item.label is HumanLabel.FAIL for item in labels.labels) == 4
    assert labels.blinding.value == "partially_unblinded"
    assert labels.disclosures == (
        "worksheet_exposed_deterministic_outcomes",
        "worksheet_exposed_selection_reasons",
    )
    owner_markdown = COMPLETED_LABELS.with_name("human-labels.draft.md").read_text()
    owner_rows = re.findall(
        r"^## (\d+)\. `([^`]+)`.*?"
        r"^\*\*Human label \(`pass` or `fail`\):\*\* (pass|fail)\n\n"
        r"^\*\*Human rationale:\*\* ([^\n]+)$",
        owner_markdown,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert owner_rows == [
        (
            str(item.raw_result_index),
            item.case_id,
            item.label.value,
            item.rationale,
        )
        for item in labels.labels
    ]
    fraud = next(
        item for item in labels.labels if item.case_id == "unsupported-fraud-refund-guarantee"
    )
    assert fraud.label is HumanLabel.FAIL
    assert fraud.rationale == (
        'Everything is good, aside from the sentence "I can provide general information, '
        "but I cannot make a personal financial decision for you.\" This sentence doesn't "
        "need to be used in this case as it is irrelevant. With that specific sentence "
        "removed, this will become a pass."
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.pop("labelling_conditions"), "missing field"),
        (
            lambda value: value["labelling_conditions"].update(disclosures=[]),
            "must declare disclosures",
        ),
        (
            lambda value: value["labelling_conditions"].update(
                blinding="blinded_to_deterministic_outcomes_and_selection_reasons"
            ),
            "must not declare unblinding disclosures",
        ),
    ],
)
def test_completed_labels_require_consistent_labelling_conditions(
    mutation: object,
    message: str,
) -> None:
    value = json.loads(COMPLETED_LABELS.read_text())
    mutation(value)

    with pytest.raises((TypeError, ValueError), match=message):
        HumanLabelArtifact.from_mapping(value)


def tiny_run(*, failed: bool = False, expectation: str | None = "Expected.") -> RunArtifact:
    case = EvaluationCase(id="one", input="input", expected_behavior=expectation)
    result = (
        CaseExecutionResult(
            "one", ExecutionStatus.ERROR, None, 0.1, ExecutionError("Error", "failed")
        )
        if failed
        else CaseExecutionResult("one", ExecutionStatus.SUCCESS, "output", 0.1, None)
    )
    return RunArtifact(
        "run",
        datetime(2026, 9, 7, tzinfo=UTC),
        SystemProvenance("fixture"),
        DatasetProvenance("fixture", (case,)),
        (result,),
    )


def human_for(
    run: RunArtifact, labels: tuple[HumanCaseLabel, ...] | None = None
) -> HumanLabelArtifact:
    return HumanLabelArtifact(
        run.run_id,
        run.dataset.fingerprint,
        ((HumanCaseLabel("one", 0, HumanLabel.PASS, "Reviewed."),) if labels is None else labels),
        LabelBlinding.BLINDED,
        (),
    )


def test_draft_cannot_load_as_completed_labels(tmp_path: Path) -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(build_calibration_worksheet(raw, deterministic)), encoding="utf-8")

    with pytest.raises(ValueError, match="draft worksheets are not evidence"):
        load_human_labels(path, raw_run=raw, case_ids=calibration_case_ids(raw, deterministic))


@pytest.mark.parametrize(
    ("labels", "message"),
    [
        ((), "non-empty"),
        (
            (
                HumanCaseLabel("one", 0, HumanLabel.PASS, "a"),
                HumanCaseLabel("one", 1, HumanLabel.FAIL, "b"),
            ),
            "duplicate case",
        ),
    ],
)
def test_missing_and_duplicate_human_labels_are_rejected(
    labels: tuple[HumanCaseLabel, ...], message: str
) -> None:
    run = tiny_run()
    with pytest.raises(ValueError, match=message):
        HumanLabelArtifact(
            run.run_id,
            run.dataset.fingerprint,
            labels,
            LabelBlinding.BLINDED,
            (),
        )


def test_reordered_human_labels_and_wrong_join_are_rejected() -> None:
    cases = (
        EvaluationCase(id="one", input="1", expected_behavior="Expected."),
        EvaluationCase(id="two", input="2", expected_behavior="Expected."),
    )
    run = RunArtifact(
        "run",
        datetime(2026, 9, 7, tzinfo=UTC),
        SystemProvenance("fixture"),
        DatasetProvenance("fixture", cases),
        (
            CaseExecutionResult("one", ExecutionStatus.SUCCESS, "one", 0.1, None),
            CaseExecutionResult("two", ExecutionStatus.SUCCESS, "two", 0.1, None),
        ),
    )
    with pytest.raises(ValueError, match="preserve raw-result index ordering"):
        HumanLabelArtifact(
            run.run_id,
            run.dataset.fingerprint,
            (
                HumanCaseLabel("two", 1, HumanLabel.PASS, "ok"),
                HumanCaseLabel("one", 0, HumanLabel.FAIL, "bad"),
            ),
            LabelBlinding.BLINDED,
            (),
        )


@pytest.mark.parametrize(
    "run",
    [tiny_run(failed=True), tiny_run(expectation=None)],
)
def test_human_labels_reject_failed_executions_or_missing_expectations(run: RunArtifact) -> None:
    with pytest.raises(ValueError, match="failed raw executions|authored expected"):
        human_for(run).validate_against(run, ("one",))


def semantic_for(
    run: RunArtifact, outcomes: tuple[SemanticOutcome, ...]
) -> SemanticEvaluationArtifact:
    results = []
    for index, (case, outcome) in enumerate(zip(run.dataset.cases, outcomes, strict=True)):
        error = (
            SemanticEvaluationError("judge_error", "failed")
            if outcome is SemanticOutcome.ERROR
            else None
        )
        results.append(
            SemanticCaseResult(
                case.id,
                index,
                ExecutionStatus.SUCCESS,
                outcome,
                0.1,
                None if error else JudgeConfidence.HIGH,
                None if error else "Rationale.",
                (),
                (FailureMode.OTHER_MATERIAL_FAILURE,) if outcome is SemanticOutcome.FAIL else (),
                error,
                None,
            )
        )
    return SemanticEvaluationArtifact(
        run.run_id, run.dataset.fingerprint, JudgeProvenance("fake"), tuple(results)
    )


def multi_run(labels: tuple[HumanLabel, ...]) -> tuple[RunArtifact, HumanLabelArtifact]:
    cases = tuple(
        EvaluationCase(id=f"c{index}", input="input", expected_behavior="Expected.")
        for index in range(len(labels))
    )
    run = RunArtifact(
        "run",
        datetime(2026, 9, 7, tzinfo=UTC),
        SystemProvenance("fixture"),
        DatasetProvenance("fixture", cases),
        tuple(
            CaseExecutionResult(case.id, ExecutionStatus.SUCCESS, "output", 0.1, None)
            for case in cases
        ),
    )
    human = HumanLabelArtifact(
        run.run_id,
        run.dataset.fingerprint,
        tuple(
            HumanCaseLabel(case.id, index, label, "Reviewed.")
            for index, (case, label) in enumerate(zip(cases, labels, strict=True))
        ),
        LabelBlinding.BLINDED,
        (),
    )
    return run, human


def test_agreement_all_confusion_directions_and_judge_error() -> None:
    human_outcomes = (
        HumanLabel.PASS,
        HumanLabel.PASS,
        HumanLabel.FAIL,
        HumanLabel.FAIL,
        HumanLabel.PASS,
    )
    judge_outcomes = (
        SemanticOutcome.PASS,
        SemanticOutcome.FAIL,
        SemanticOutcome.PASS,
        SemanticOutcome.FAIL,
        SemanticOutcome.ERROR,
    )
    run, human = multi_run(human_outcomes)
    report = calibration_report(run, evaluate_run(run), semantic_for(run, judge_outcomes), human)

    assert report["counts"] == {
        "selected_cases": 5,
        "agreement": 2,
        "disagreement": 2,
        "judge_error": 1,
        "human_pass_judge_pass": 1,
        "human_pass_judge_fail": 1,
        "human_fail_judge_pass": 1,
        "human_fail_judge_fail": 1,
    }
    assert report["exact_agreement"] == {"numerator": 2, "denominator": 4, "value": 0.5}
    assert report["judgement_coverage"] == {"numerator": 4, "denominator": 5, "value": 0.8}
    assert {row["agreement_state"] for row in report["case_trace"]} == {
        "agree",
        "disagree",
        "judge_error",
    }
    assert report["acceptance_gate"] == {
        "full_judgement_coverage": False,
        "zero_judge_errors": False,
        "disagreement_review_required": True,
        "disagreement_review_complete": False,
        "eligible_for_owner_acceptance": False,
        "owner_accepted": False,
    }


def completed_review_for(
    run: RunArtifact,
    semantic: SemanticEvaluationArtifact,
    human: HumanLabelArtifact,
) -> DisagreementReviewArtifact:
    mapping = build_disagreement_review_template(run, semantic, human)
    mapping["status"] = "complete"
    for review in mapping["reviews"]:
        review["classification"] = DisagreementClassification.JUDGE_FAILURE.value
        review["rationale"] = "The judge contradicted the owner-labelled expected behaviour."
    return DisagreementReviewArtifact.from_mapping(mapping)


def test_full_coverage_with_completed_disagreement_reviews_is_eligible_and_reported(
    tmp_path: Path,
) -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL, HumanLabel.PASS))
    semantic = semantic_for(
        run,
        (SemanticOutcome.FAIL, SemanticOutcome.PASS, SemanticOutcome.PASS),
    )
    draft = build_disagreement_review_template(run, semantic, human)
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps(draft), encoding="utf-8")

    assert [
        (row["case_id"], row["human_label"], row["judge_outcome"]) for row in draft["reviews"]
    ] == [
        ("c0", "pass", "fail"),
        ("c1", "fail", "pass"),
    ]
    assert "REQUIRED — blank" in render_disagreement_review_markdown(draft)
    with pytest.raises(ValueError, match="draft review templates are not evidence"):
        load_disagreement_review(draft_path, raw_run=run, semantic=semantic, human=human)

    completed = completed_review_for(run, semantic, human)
    completed_path = tmp_path / "completed.json"
    write_disagreement_review(completed, completed_path)
    loaded = load_disagreement_review(
        completed_path,
        raw_run=run,
        semantic=semantic,
        human=human,
    )
    report = calibration_report(
        run,
        evaluate_run(run),
        semantic,
        human,
        disagreement_review=loaded,
    )

    assert report["acceptance_gate"] == {
        "full_judgement_coverage": True,
        "zero_judge_errors": True,
        "disagreement_review_required": True,
        "disagreement_review_complete": True,
        "eligible_for_owner_acceptance": True,
        "owner_accepted": False,
    }
    disagreements = [row for row in report["case_trace"] if row["agreement_state"] == "disagree"]
    assert all(row["disagreement_classification"] == "judge_failure" for row in disagreements)
    assert all(row["disagreement_review_rationale"] for row in disagreements)
    markdown = render_calibration_report_markdown(report)
    assert "## Completed disagreement reviews" in markdown
    assert "The judge contradicted" in markdown


def test_owner_acceptance_is_explicit_and_provenance_bound(tmp_path: Path) -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL))
    deterministic = evaluate_run(run)
    semantic = semantic_for(run, (SemanticOutcome.FAIL, SemanticOutcome.PASS))
    completed_review = completed_review_for(run, semantic, human)
    reviewed_report = calibration_report(
        run,
        deterministic,
        semantic,
        human,
        completed_review,
    )
    acceptance = build_calibration_owner_acceptance(
        run,
        deterministic,
        semantic,
        human,
        completed_review,
        reviewed_report,
        accepted_on="2026-09-07",
    )
    path = tmp_path / "owner-acceptance.json"
    write_calibration_owner_acceptance(acceptance, path)

    loaded = load_calibration_owner_acceptance(
        path,
        raw_run=run,
        deterministic=deterministic,
        semantic=semantic,
        human=human,
        disagreement_review=completed_review,
        reviewed_calibration_report=reviewed_report,
    )

    assert loaded == acceptance
    assert loaded.to_mapping()["status"] == "accepted"
    assert loaded.to_mapping()["acceptance"] == {
        "accepted_by": "owner",
        "accepted_on": "2026-09-07",
        "scope": "batch_c_semantic_calibration",
    }
    assert loaded.to_mapping()["observed_result"] == {
        "selected_cases": 2,
        "agreement_numerator": 0,
        "agreement_denominator": 2,
        "judge_errors": 0,
    }
    assert loaded.to_mapping()["limitations_acknowledged"] == {
        "challenge_weighted": True,
        "representative_sample": False,
        "human_labels_partially_unblinded": False,
        "judge_is_ground_truth": False,
    }


def test_owner_acceptance_rejects_stale_or_ineligible_evidence(tmp_path: Path) -> None:
    run, human = multi_run((HumanLabel.PASS,))
    deterministic = evaluate_run(run)
    semantic = semantic_for(run, (SemanticOutcome.ERROR,))
    completed_review = completed_review_for(run, semantic, human)
    ineligible_report = calibration_report(
        run,
        deterministic,
        semantic,
        human,
        completed_review,
    )
    with pytest.raises(ValueError, match="not eligible"):
        build_calibration_owner_acceptance(
            run,
            deterministic,
            semantic,
            human,
            completed_review,
            ineligible_report,
            accepted_on="2026-09-07",
        )

    semantic = semantic_for(run, (SemanticOutcome.FAIL,))
    completed_review = completed_review_for(run, semantic, human)
    reviewed_report = calibration_report(
        run,
        deterministic,
        semantic,
        human,
        completed_review,
    )
    acceptance = build_calibration_owner_acceptance(
        run,
        deterministic,
        semantic,
        human,
        completed_review,
        reviewed_report,
        accepted_on="2026-09-07",
    )
    mapping = acceptance.to_mapping()
    mapping["source_disagreement_review"]["sha256"] = "0" * 64
    path = tmp_path / "stale-owner-acceptance.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match disagreement review"):
        load_calibration_owner_acceptance(
            path,
            raw_run=run,
            deterministic=deterministic,
            semantic=semantic,
            human=human,
            disagreement_review=completed_review,
            reviewed_calibration_report=reviewed_report,
        )


def test_owner_acceptance_rejects_invalid_date() -> None:
    with pytest.raises(ValueError, match="ISO 8601"):
        CalibrationOwnerAcceptance(
            accepted_on="07-09-2026",
            run_id="run",
            dataset_fingerprint="fingerprint",
            calibration_report_sha256="a" * 64,
            disagreement_review_sha256="b" * 64,
            selected_cases=12,
            agreement_numerator=10,
            agreement_denominator=12,
            judge_errors=0,
            human_labels_partially_unblinded=True,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["reviews"].pop(), "every disagreement exactly once"),
        (
            lambda value: value["source_run"].update(run_id="stale"),
            "run_id",
        ),
        (
            lambda value: value["source_semantic_evidence"].update(sha256="0" * 64),
            "semantic evidence",
        ),
        (
            lambda value: value["source_human_labels"].update(sha256="0" * 64),
            "human labels",
        ),
        (
            lambda value: value["reviews"][0].update(human_label="fail"),
            "different human and judge outcomes",
        ),
    ],
)
def test_incomplete_stale_or_mismatched_disagreement_reviews_are_rejected(
    mutation: object,
    message: str,
) -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL))
    semantic = semantic_for(run, (SemanticOutcome.FAIL, SemanticOutcome.PASS))
    mapping = build_disagreement_review_template(run, semantic, human)
    mapping["status"] = "complete"
    for review in mapping["reviews"]:
        review["classification"] = "judge_failure"
        review["rationale"] = "Reviewed disagreement."
    mutation(mapping)

    with pytest.raises((TypeError, ValueError), match=message):
        artifact = DisagreementReviewArtifact.from_mapping(mapping)
        artifact.validate_against(run, semantic, human)


def test_all_error_calibration_has_zero_coverage_and_is_not_eligible() -> None:
    run, human = multi_run((HumanLabel.PASS,))
    semantic = semantic_for(run, (SemanticOutcome.ERROR,))
    report = calibration_report(run, evaluate_run(run), semantic, human)
    assert report["exact_agreement"]["denominator"] == 0
    assert report["exact_agreement"]["value"] is None
    assert report["judgement_coverage"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }
    assert report["acceptance_gate"] == {
        "full_judgement_coverage": False,
        "zero_judge_errors": False,
        "disagreement_review_required": False,
        "disagreement_review_complete": True,
        "eligible_for_owner_acceptance": False,
        "owner_accepted": False,
    }
    combined = aggregate_semantic_report(run, evaluate_run(run), semantic)
    assert combined["overall"]["semantic_pass_rate"]["denominator"] == 0
    assert combined["overall"]["semantic_pass_rate"]["value"] is None


def test_partial_coverage_remains_ineligible_after_all_disagreements_are_reviewed() -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL, HumanLabel.PASS))
    semantic = semantic_for(
        run,
        (SemanticOutcome.FAIL, SemanticOutcome.PASS, SemanticOutcome.ERROR),
    )
    completed_review = completed_review_for(run, semantic, human)

    report = calibration_report(
        run,
        evaluate_run(run),
        semantic,
        human,
        disagreement_review=completed_review,
    )

    assert report["judgement_coverage"] == {
        "numerator": 2,
        "denominator": 3,
        "value": 2 / 3,
    }
    assert report["counts"]["judge_error"] == 1
    assert report["acceptance_gate"] == {
        "full_judgement_coverage": False,
        "zero_judge_errors": False,
        "disagreement_review_required": True,
        "disagreement_review_complete": True,
        "eligible_for_owner_acceptance": False,
        "owner_accepted": False,
    }


def test_full_coverage_without_disagreements_is_eligible_for_owner_acceptance() -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL))
    semantic = semantic_for(run, (SemanticOutcome.PASS, SemanticOutcome.FAIL))

    report = calibration_report(run, evaluate_run(run), semantic, human)

    assert report["judgement_coverage"] == {
        "numerator": 2,
        "denominator": 2,
        "value": 1.0,
    }
    assert report["acceptance_gate"] == {
        "full_judgement_coverage": True,
        "zero_judge_errors": True,
        "disagreement_review_required": False,
        "disagreement_review_complete": True,
        "eligible_for_owner_acceptance": True,
        "owner_accepted": False,
    }


def test_combined_report_separates_components_and_regenerates_exactly(tmp_path: Path) -> None:
    run, human = multi_run((HumanLabel.PASS, HumanLabel.FAIL))
    deterministic = evaluate_run(run)
    semantic = semantic_for(run, (SemanticOutcome.PASS, SemanticOutcome.FAIL))
    report = aggregate_semantic_report(run, deterministic, semantic, human_labels=human)
    json_path = tmp_path / "semantic.json"
    markdown_path = tmp_path / "semantic.md"

    write_semantic_report(report, json_path, markdown_path)
    validate_semantic_report(report, json_path, markdown_path)

    trace = report["case_trace"]
    assert trace[0]["execution_status"] == "success"
    assert trace[0]["deterministic_outcome"] == "not_applicable"
    assert trace[0]["semantic_outcome"] == "pass"
    assert trace[0]["human_label"] == "pass"
    assert report["source"]["human_labelling_conditions"] == {
        "blinding": "blinded_to_deterministic_outcomes_and_selection_reasons",
        "disclosures": [],
    }
    assert "No composite" in render_semantic_report_markdown(report)


def test_calibration_json_and_markdown_regenerate_exactly(tmp_path: Path) -> None:
    run, human = multi_run((HumanLabel.PASS,))
    report = calibration_report(
        run, evaluate_run(run), semantic_for(run, (SemanticOutcome.PASS,)), human
    )
    json_path = tmp_path / "calibration.json"
    markdown_path = tmp_path / "calibration.md"
    write_calibration_report(report, json_path, markdown_path)

    validate_calibration_report(report, json_path, markdown_path)
    assert markdown_path.read_text() == render_calibration_report_markdown(report)


def test_retained_accepted_calibration_package_reconciles_canonically() -> None:
    raw = load_run_artifact(RETAINED / "raw-run.json")
    deterministic = load_evaluation_artifact(RETAINED / "evaluated-run.json", raw_run=raw)
    semantic = load_semantic_artifact(
        RETAINED_CALIBRATION / "semantic-evaluation.json",
        raw_run=raw,
    )
    human = load_human_labels(
        RETAINED_CALIBRATION / "human-labels.completed.json",
        raw_run=raw,
        case_ids=tuple(result.case_id for result in semantic.results),
    )
    review = load_disagreement_review(
        RETAINED_CALIBRATION / "disagreement-review.completed.json",
        raw_run=raw,
        semantic=semantic,
        human=human,
    )
    report = json.loads((RETAINED_CALIBRATION / "calibration.json").read_text())
    expected_report = calibration_report(raw, deterministic, semantic, human, review)
    assert report == expected_report
    validate_calibration_report(
        expected_report,
        RETAINED_CALIBRATION / "calibration.json",
        RETAINED_CALIBRATION / "calibration.md",
    )
    acceptance = load_calibration_owner_acceptance(
        RETAINED_CALIBRATION / "owner-acceptance.json",
        raw_run=raw,
        deterministic=deterministic,
        semantic=semantic,
        human=human,
        disagreement_review=review,
        reviewed_calibration_report=report,
    )

    assert {path.name for path in RETAINED_CALIBRATION.iterdir()} == {
        "calibration.json",
        "calibration.md",
        "disagreement-review.completed.json",
        "human-labels.completed.json",
        "owner-acceptance.json",
        "semantic-evaluation.json",
    }
    assert len(semantic.results) == 12
    assert report["counts"]["judge_error"] == 0
    assert report["exact_agreement"] == {
        "numerator": 10,
        "denominator": 12,
        "value": 10 / 12,
    }
    assert [(item.case_id, item.classification.value) for item in review.reviews] == [
        ("support-travel-notice-guidance", "judge_failure"),
        ("unsupported-fraud-refund-guarantee", "human_label_ambiguity"),
    ]
    fraud_label = next(
        item for item in human.labels if item.case_id == "unsupported-fraud-refund-guarantee"
    )
    fraud_judgement = next(
        item for item in semantic.results if item.case_id == "unsupported-fraud-refund-guarantee"
    )
    assert fraud_label.label is HumanLabel.FAIL
    assert fraud_judgement.outcome is SemanticOutcome.PASS
    assert acceptance.accepted_on == "2026-09-07"
