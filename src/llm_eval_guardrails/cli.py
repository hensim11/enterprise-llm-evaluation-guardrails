"""Small local command-line entry point for implemented workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from llm_eval_guardrails.run_artifact import write_run_artifact
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

    parser.error(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
