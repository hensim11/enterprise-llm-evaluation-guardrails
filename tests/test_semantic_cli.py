import json
from pathlib import Path

import pytest

from llm_eval_guardrails import JudgeConfidence, SemanticJudgment, SemanticOutcome
from llm_eval_guardrails.cli import main

RETAINED = Path("evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906")
COMPLETED_LABELS = Path(
    "evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json"
)


def test_prepare_calibration_publishes_two_draft_files_and_refuses_collision(
    tmp_path: Path,
) -> None:
    output = tmp_path / "worksheet"
    arguments = [
        "prepare-semantic-calibration",
        str(RETAINED / "raw-run.json"),
        str(RETAINED / "evaluated-run.json"),
        str(output),
    ]

    assert main(arguments) == 0
    assert {path.name for path in output.iterdir()} == {
        "human-labels.draft.json",
        "human-labels.draft.md",
    }
    assert "DRAFT / INCOMPLETE" in (output / "human-labels.draft.md").read_text()
    with pytest.raises(FileExistsError, match="already exists"):
        main(arguments)


def test_prepare_calibration_removes_stage_after_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "failed"

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("worksheet failed")

    monkeypatch.setattr("llm_eval_guardrails.cli.write_calibration_worksheet", fail)
    with pytest.raises(RuntimeError, match="worksheet failed"):
        main(
            [
                "prepare-semantic-calibration",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(output),
            ]
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".failed.staging-*"))


def test_prepare_blinded_calibration_omits_prior_outcomes_and_selection_reasons(
    tmp_path: Path,
) -> None:
    output = tmp_path / "blinded"

    assert (
        main(
            [
                "prepare-semantic-calibration",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(output),
                "--blinded",
            ]
        )
        == 0
    )

    worksheet = json.loads((output / "human-labels.draft.json").read_text())
    markdown = (output / "human-labels.draft.md").read_text()
    assert worksheet["labelling_conditions"]["hidden_fields"] == [
        "deterministic_outcome",
        "selection_reason",
    ]
    assert all("deterministic_outcome" not in row for row in worksheet["cases"])
    assert all("selection_reason" not in row for row in worksheet["cases"])
    assert "Deterministic outcome" not in markdown
    assert "Selection:" not in markdown


def test_validate_completed_owner_labels_cli() -> None:
    assert (
        main(
            [
                "validate-human-labels",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(COMPLETED_LABELS),
            ]
        )
        == 0
    )


def test_openai_semantic_cli_uses_fixed_subset_with_sdk_shaped_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class FakeJudge:
        sdk_version = "1.66.0-test"
        provenance = {
            "provider": "openai",
            "api": "responses",
            "sdk_version": sdk_version,
            "model": "test-model",
            "prompt_version": "semantic-judge-v1",
            "output_schema_version": "1",
            "max_output_tokens": 123,
            "max_retries": 0,
            "store": False,
        }

        def __init__(self, *, model: str, max_output_tokens: int) -> None:
            assert model == "test-model"
            assert max_output_tokens == 123

        def judge(self, request: object) -> SemanticJudgment:
            calls.append(request)
            return SemanticJudgment(
                SemanticOutcome.PASS,
                JudgeConfidence.HIGH,
                "The response satisfies the authored behaviour.",
            )

    monkeypatch.setattr(
        "llm_eval_guardrails.openai_semantic_judge.OpenAIResponsesSemanticJudge",
        FakeJudge,
    )
    output = tmp_path / "semantic"

    assert (
        main(
            [
                "run-openai-semantic",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(output),
                "--model",
                "test-model",
                "--max-output-tokens",
                "123",
                "--calibration-subset",
                "--human-labels",
                str(COMPLETED_LABELS),
                "--guardrail-decisions",
                str(RETAINED / "guardrail-decisions.json"),
            ]
        )
        == 0
    )

    assert len(calls) == 12
    assert {path.name for path in output.iterdir()} == {
        "semantic-evaluation.json",
        "semantic-summary.json",
        "semantic-report.md",
    }
    report = (output / "semantic-report.md").read_text()
    assert "Deterministic pass / fail" in report
    assert "| block |" in report
    combined = json.loads((output / "semantic-summary.json").read_text())
    assert combined["overall"]["human_labels"] == {
        "pass": 8,
        "fail": 4,
        "unavailable": 0,
    }
    assert combined["source"]["human_labelling_conditions"]["blinding"] == ("partially_unblinded")

    first_report = tmp_path / "calibration-with-draft"
    assert (
        main(
            [
                "report-semantic-calibration",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(output / "semantic-evaluation.json"),
                str(COMPLETED_LABELS),
                str(first_report),
            ]
        )
        == 0
    )
    assert {path.name for path in first_report.iterdir()} == {
        "calibration.json",
        "calibration.md",
        "disagreement-review.draft.json",
        "disagreement-review.draft.md",
    }
    initial = json.loads((first_report / "calibration.json").read_text())
    assert initial["counts"]["disagreement"] == 4
    assert initial["acceptance_gate"]["eligible_for_owner_acceptance"] is False

    review = json.loads((first_report / "disagreement-review.draft.json").read_text())
    review["status"] = "complete"
    for row in review["reviews"]:
        row["classification"] = "judge_failure"
        row["rationale"] = "Fixture judge intentionally returned pass for every case."
    completed_review = tmp_path / "disagreement-review.completed.json"
    completed_review.write_text(json.dumps(review), encoding="utf-8")

    accepted_report = tmp_path / "calibration-reviewed"
    assert (
        main(
            [
                "report-semantic-calibration",
                str(RETAINED / "raw-run.json"),
                str(RETAINED / "evaluated-run.json"),
                str(output / "semantic-evaluation.json"),
                str(COMPLETED_LABELS),
                str(accepted_report),
                "--disagreement-review",
                str(completed_review),
            ]
        )
        == 0
    )
    assert {path.name for path in accepted_report.iterdir()} == {
        "calibration.json",
        "calibration.md",
    }
    reviewed = json.loads((accepted_report / "calibration.json").read_text())
    assert reviewed["acceptance_gate"]["disagreement_review_complete"] is True
    assert reviewed["acceptance_gate"]["eligible_for_owner_acceptance"] is True
    assert {
        row["disagreement_classification"]
        for row in reviewed["case_trace"]
        if row["agreement_state"] == "disagree"
    } == {"judge_failure"}
