from pathlib import Path

import pytest

from llm_eval_guardrails import SystemResponse, load_evaluation_artifact, load_run_artifact
from llm_eval_guardrails.cli import main


def test_run_echo_command_writes_labelled_synthetic_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"input"}\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "run.json"

    exit_status = main(
        [
            "run-echo",
            str(dataset_path),
            str(output_path),
            "--run-id",
            "cli-test",
        ]
    )

    artifact = load_run_artifact(output_path)
    assert exit_status == 0
    assert artifact.run_id == "cli-test"
    assert artifact.system.id == "echo"
    assert artifact.results[0].output == "input"
    assert "synthetic echo plumbing artefact" in capsys.readouterr().out


def test_evaluate_command_atomically_writes_three_reconciled_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"schema_version":"1","id":"one","input":"answer",'
        '"assertions":[{"criterion":"exact","type":"exact_match","value":"answer"}]}\n',
        encoding="utf-8",
    )
    raw_path = tmp_path / "raw.json"
    assert main(["run-echo", str(dataset), str(raw_path), "--run-id", "offline"]) == 0
    output_directory = tmp_path / "evaluated"

    assert main(["evaluate", str(raw_path), str(output_directory)]) == 0

    raw = load_run_artifact(raw_path)
    evaluated = load_evaluation_artifact(output_directory / "evaluated-run.json", raw_run=raw)
    summary = __import__("json").loads(
        (output_directory / "summary.json").read_text(encoding="utf-8")
    )
    markdown = (output_directory / "report.md").read_text(encoding="utf-8")
    assert evaluated.results[0].outcome.value == "pass"
    assert summary["overall"]["assertion_pass_rate"]["value"] == 1.0
    assert "1/1 (100.0%)" in markdown
    assert "atomically" in capsys.readouterr().out


def test_evaluate_command_refuses_overwrite(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text('{"schema_version":"1","id":"one","input":"answer"}\n', encoding="utf-8")
    raw_path = tmp_path / "raw.json"
    main(["run-echo", str(dataset), str(raw_path)])
    output_directory = tmp_path / "already-exists"
    output_directory.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        main(["evaluate", str(raw_path), str(output_directory)])


def test_partial_evaluation_bundle_is_removed_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text('{"schema_version":"1","id":"one","input":"answer"}\n', encoding="utf-8")
    raw_path = tmp_path / "raw.json"
    main(["run-echo", str(dataset), str(raw_path)])
    output_directory = tmp_path / "failed-bundle"

    def fail_report(*args: object, **kwargs: object) -> None:
        raise RuntimeError("report failed")

    monkeypatch.setattr("llm_eval_guardrails.cli.write_json_report", fail_report)

    with pytest.raises(RuntimeError, match="report failed"):
        main(["evaluate", str(raw_path), str(output_directory)])

    assert not output_directory.exists()
    assert not list(tmp_path.glob(".failed-bundle.staging-*"))


def test_run_openai_command_uses_injected_adapter_and_writes_complete_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        '{"schema_version":"1","id":"one","input":"customer input",'
        '"context":["ordered context"],'
        '"assertions":[{"criterion":"exact","type":"exact_match",'
        '"value":"Northstar demo complete."}]}\n',
        encoding="utf-8",
    )
    requests = []

    class FakeOpenAIAdapter:
        sdk_version = "1.66.0-test"

        def __init__(self, *, model: str, max_output_tokens: int) -> None:
            assert model == "test-model-2026-01-01"
            assert max_output_tokens == 250

        def invoke(self, request: object) -> SystemResponse:
            requests.append(request)
            return SystemResponse("Northstar demo complete.")

    monkeypatch.setattr(
        "llm_eval_guardrails.openai_adapter.OpenAIResponsesSystem", FakeOpenAIAdapter
    )
    output_directory = tmp_path / "openai-bundle"

    assert (
        main(
            [
                "run-openai",
                str(dataset),
                str(output_directory),
                "--model",
                "test-model-2026-01-01",
                "--max-output-tokens",
                "250",
                "--run-id",
                "provider-cli",
            ]
        )
        == 0
    )

    assert {path.name for path in output_directory.iterdir()} == {
        "raw-run.json",
        "evaluated-run.json",
        "summary.json",
        "report.md",
    }
    raw = load_run_artifact(output_directory / "raw-run.json")
    evaluated = load_evaluation_artifact(output_directory / "evaluated-run.json", raw_run=raw)
    assert raw.run_id == "provider-cli"
    assert raw.system.configuration["model"] == "test-model-2026-01-01"
    assert raw.system.configuration["sdk_version"] == "1.66.0-test"
    assert "api_key" not in str(raw.to_mapping())
    assert evaluated.results[0].outcome.value == "pass"
    assert requests[0].input == "customer input"
    assert requests[0].context == ("ordered context",)
