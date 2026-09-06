"""Small local command-line entry point for implemented workflows."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from llm_eval_guardrails.evaluation_artifact import (
    load_evaluation_artifact,
    write_evaluation_artifact,
)
from llm_eval_guardrails.evaluator import evaluate_run
from llm_eval_guardrails.reporting import (
    aggregate_run,
    validate_json_report,
    validate_markdown_report,
    write_json_report,
    write_markdown_report,
)
from llm_eval_guardrails.run_artifact import load_run_artifact, write_run_artifact
from llm_eval_guardrails.runner import run_dataset
from llm_eval_guardrails.system_under_test import EchoSystemUnderTest


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit status."""
    parser = argparse.ArgumentParser(prog="llm-eval-guardrails")
    subparsers = parser.add_subparsers(dest="command", required=True)
    echo_parser = subparsers.add_parser(
        "run-echo",
        help="write a synthetic echo-system plumbing run artefact",
    )
    echo_parser.add_argument("dataset", type=Path)
    echo_parser.add_argument("output", type=Path)
    echo_parser.add_argument("--run-id")

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="evaluate an existing raw run and atomically publish evidence and reports",
    )
    evaluate_parser.add_argument("raw_run", type=Path)
    evaluate_parser.add_argument("output_directory", type=Path)

    openai_parser = subparsers.add_parser(
        "run-openai",
        help="run, evaluate, and report the benchmark with an explicit OpenAI model",
    )
    openai_parser.add_argument("dataset", type=Path)
    openai_parser.add_argument("output_directory", type=Path)
    openai_parser.add_argument("--model", required=True)
    openai_parser.add_argument("--max-output-tokens", type=int, default=800)
    openai_parser.add_argument("--run-id")
    args = parser.parse_args(argv)

    if args.command == "run-echo":
        artifact = run_dataset(
            args.dataset,
            EchoSystemUnderTest(),
            system_id="echo",
            system_configuration={
                "behavior": "input_verbatim",
                "context_usage": "ignored",
            },
            run_id=args.run_id,
        )
        write_run_artifact(artifact, args.output)
        print(
            "Wrote synthetic echo plumbing artefact "
            f"with {len(artifact.results)} case results to {args.output}"
        )
        return 0

    if args.command == "evaluate":
        raw_run = load_run_artifact(args.raw_run)

        def build_evaluation(stage: Path) -> None:
            evaluated = evaluate_run(raw_run)
            evaluated_path = stage / "evaluated-run.json"
            summary_path = stage / "summary.json"
            markdown_path = stage / "report.md"
            write_evaluation_artifact(evaluated, evaluated_path)
            persisted_evaluation = load_evaluation_artifact(evaluated_path, raw_run=raw_run)
            report = aggregate_run(
                raw_run,
                persisted_evaluation,
                raw_evidence_path=str(args.raw_run.resolve()),
                evaluated_evidence_path="evaluated-run.json",
            )
            write_json_report(report, summary_path)
            write_markdown_report(report, markdown_path)
            validate_json_report(report, summary_path)
            validate_markdown_report(report, markdown_path)

        _publish_directory(args.output_directory, build_evaluation)
        print(
            "Wrote evaluated-run.json, summary.json, and report.md atomically to "
            f"{args.output_directory}"
        )
        return 0

    if args.command == "run-openai":
        from llm_eval_guardrails.openai_adapter import (
            OpenAIResponsesSystem,
            openai_provenance,
        )

        system = OpenAIResponsesSystem(
            model=args.model,
            max_output_tokens=args.max_output_tokens,
        )

        def build_openai_run(stage: Path) -> None:
            raw_run = run_dataset(
                args.dataset,
                system,
                system_id="openai-responses-northstar-baseline",
                system_configuration=openai_provenance(
                    model=args.model,
                    max_output_tokens=args.max_output_tokens,
                    sdk_version=system.sdk_version,
                ),
                run_id=args.run_id,
            )
            raw_path = stage / "raw-run.json"
            evaluated_path = stage / "evaluated-run.json"
            write_run_artifact(raw_run, raw_path)
            evaluated = evaluate_run(raw_run)
            write_evaluation_artifact(evaluated, evaluated_path)
            persisted_evaluation = load_evaluation_artifact(evaluated_path, raw_run=raw_run)
            report = aggregate_run(
                raw_run,
                persisted_evaluation,
                raw_evidence_path="raw-run.json",
                evaluated_evidence_path="evaluated-run.json",
            )
            summary_path = stage / "summary.json"
            markdown_path = stage / "report.md"
            write_json_report(report, summary_path)
            write_markdown_report(report, markdown_path)
            validate_json_report(report, summary_path)
            validate_markdown_report(report, markdown_path)

        _publish_directory(args.output_directory, build_openai_run)
        print(
            "Wrote raw-run.json, evaluated-run.json, summary.json, and report.md "
            f"atomically to {args.output_directory}"
        )
        return 0

    parser.error(f"unsupported command: {args.command}")


def _publish_directory(output_directory: Path, build: Callable[[Path], None]) -> None:
    """Publish a complete new output directory with one same-filesystem rename."""
    if output_directory.exists():
        raise FileExistsError(f"output directory already exists: {output_directory}")
    parent = output_directory.parent
    if not parent.is_dir():
        raise FileNotFoundError(f"output directory parent does not exist: {parent}")
    stage = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.staging-", dir=parent))
    try:
        build(stage)
        stage.rename(output_directory)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
