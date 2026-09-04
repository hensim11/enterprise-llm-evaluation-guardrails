from pathlib import Path

import pytest

from llm_eval_guardrails import load_run_artifact
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
