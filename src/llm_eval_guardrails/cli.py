"""Small local command-line entry point for implemented workflows."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from llm_eval_guardrails.calibration import (
    build_blinded_calibration_worksheet,
    build_calibration_worksheet,
    build_disagreement_review_template,
    calibration_case_ids,
    calibration_report,
    load_disagreement_review,
    load_human_labels,
    validate_calibration_report,
    write_calibration_report,
    write_calibration_worksheet,
    write_disagreement_review_template,
)
from llm_eval_guardrails.comparison import (
    COMPARISON_MODE_CONFIGURATION_KEY,
    ComparisonEvidencePaths,
    ComparisonMode,
    EvidencePathBase,
    EvidenceReference,
    compare_runs,
    validate_comparison_artifact,
    validate_comparison_markdown,
    write_comparison_artifact,
    write_comparison_markdown,
)
from llm_eval_guardrails.dataset import load_dataset
from llm_eval_guardrails.evaluation_artifact import (
    EvaluationArtifact,
    load_evaluation_artifact,
    write_evaluation_artifact,
)
from llm_eval_guardrails.evaluator import evaluate_run
from llm_eval_guardrails.guardrail_artifact import (
    load_guardrail_artifact,
    write_guardrail_artifact,
)
from llm_eval_guardrails.guardrailed_runner import run_guardrailed_dataset
from llm_eval_guardrails.guardrails import guardrail_provenance
from llm_eval_guardrails.reporting import (
    aggregate_run,
    validate_json_report,
    validate_markdown_report,
    write_json_report,
    write_markdown_report,
)
from llm_eval_guardrails.run_artifact import (
    DatasetProvenance,
    ExecutionStatus,
    JsonValue,
    RunArtifact,
    load_run_artifact,
    write_run_artifact,
)
from llm_eval_guardrails.runner import run_dataset
from llm_eval_guardrails.semantic_artifact import (
    load_semantic_artifact,
    write_semantic_artifact,
)
from llm_eval_guardrails.semantic_evaluator import evaluate_semantically
from llm_eval_guardrails.semantic_reporting import (
    aggregate_semantic_report,
    validate_semantic_report,
    write_semantic_report,
)
from llm_eval_guardrails.system_under_test import (
    EchoSystemUnderTest,
    SystemRequest,
    SystemResponse,
    SystemUnderTest,
)


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

    replay_parser = subparsers.add_parser(
        "run-guardrailed-replay",
        help="apply guardrails to a deterministic replay and compare it with a baseline",
    )
    replay_parser.add_argument("dataset", type=Path)
    replay_parser.add_argument("baseline_directory", type=Path)
    replay_parser.add_argument("output_directory", type=Path)
    replay_parser.add_argument("--run-id")

    guarded_openai_parser = subparsers.add_parser(
        "run-openai-guardrailed",
        help="run the baseline model through guardrails and emit a matched comparison",
    )
    guarded_openai_parser.add_argument("dataset", type=Path)
    guarded_openai_parser.add_argument("baseline_directory", type=Path)
    guarded_openai_parser.add_argument("output_directory", type=Path)
    guarded_openai_parser.add_argument("--run-id")

    worksheet_parser = subparsers.add_parser(
        "prepare-semantic-calibration",
        help="create the fixed unlabelled 12-case Batch C calibration worksheet",
    )
    worksheet_parser.add_argument("raw_run", type=Path)
    worksheet_parser.add_argument("deterministic_evaluation", type=Path)
    worksheet_parser.add_argument("output_directory", type=Path)
    worksheet_parser.add_argument("--blinded", action="store_true")

    label_parser = subparsers.add_parser(
        "validate-human-labels",
        help="validate completed labels against the fixed retained calibration selection",
    )
    label_parser.add_argument("raw_run", type=Path)
    label_parser.add_argument("deterministic_evaluation", type=Path)
    label_parser.add_argument("human_labels", type=Path)

    semantic_parser = subparsers.add_parser(
        "run-openai-semantic",
        help="semantically judge retained outputs with an explicit OpenAI model",
    )
    semantic_parser.add_argument("raw_run", type=Path)
    semantic_parser.add_argument("deterministic_evaluation", type=Path)
    semantic_parser.add_argument("output_directory", type=Path)
    semantic_parser.add_argument("--model", required=True)
    semantic_parser.add_argument("--max-output-tokens", type=int, default=600)
    semantic_parser.add_argument("--calibration-subset", action="store_true")
    semantic_parser.add_argument("--case-id", action="append")
    semantic_parser.add_argument("--guardrail-decisions", type=Path)
    semantic_parser.add_argument("--human-labels", type=Path)

    calibration_parser = subparsers.add_parser(
        "report-semantic-calibration",
        help="reconcile completed human labels with semantic evidence",
    )
    calibration_parser.add_argument("raw_run", type=Path)
    calibration_parser.add_argument("deterministic_evaluation", type=Path)
    calibration_parser.add_argument("semantic_evaluation", type=Path)
    calibration_parser.add_argument("human_labels", type=Path)
    calibration_parser.add_argument("output_directory", type=Path)
    calibration_parser.add_argument("--disagreement-review", type=Path)
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

    if args.command == "prepare-semantic-calibration":
        raw_run = load_run_artifact(args.raw_run)
        deterministic = load_evaluation_artifact(args.deterministic_evaluation, raw_run=raw_run)

        def build_worksheet(stage: Path) -> None:
            worksheet = (
                build_blinded_calibration_worksheet(raw_run, deterministic)
                if args.blinded
                else build_calibration_worksheet(raw_run, deterministic)
            )
            write_calibration_worksheet(
                worksheet,
                stage / "human-labels.draft.json",
                stage / "human-labels.draft.md",
            )

        _publish_directory(args.output_directory, build_worksheet)
        print(
            "Wrote an unlabelled, incomplete 12-case calibration worksheet atomically to "
            f"{args.output_directory}"
        )
        return 0

    if args.command == "validate-human-labels":
        raw_run = load_run_artifact(args.raw_run)
        deterministic = load_evaluation_artifact(args.deterministic_evaluation, raw_run=raw_run)
        labels = load_human_labels(
            args.human_labels,
            raw_run=raw_run,
            case_ids=calibration_case_ids(raw_run, deterministic),
        )
        print(f"Validated {len(labels.labels)} completed human labels in exact calibration order")
        return 0

    if args.command == "run-openai-semantic":
        if args.calibration_subset and args.case_id:
            parser.error("--calibration-subset and --case-id cannot be combined")
        raw_run = load_run_artifact(args.raw_run)
        deterministic = load_evaluation_artifact(args.deterministic_evaluation, raw_run=raw_run)
        guardrails = (
            None
            if args.guardrail_decisions is None
            else load_guardrail_artifact(args.guardrail_decisions, raw_run=raw_run)
        )
        if args.calibration_subset:
            selected_ids = calibration_case_ids(raw_run, deterministic)
        elif args.case_id:
            selected_ids = tuple(args.case_id)
        else:
            selected_ids = None
        human_labels = (
            None
            if args.human_labels is None
            else load_human_labels(
                args.human_labels,
                raw_run=raw_run,
                case_ids=calibration_case_ids(raw_run, deterministic),
            )
        )
        from llm_eval_guardrails.openai_semantic_judge import (
            OPENAI_SEMANTIC_JUDGE_ID,
            OpenAIResponsesSemanticJudge,
        )

        judge = OpenAIResponsesSemanticJudge(
            model=args.model,
            max_output_tokens=args.max_output_tokens,
        )

        def build_semantic(stage: Path) -> None:
            semantic = evaluate_semantically(
                raw_run,
                judge,
                judge_id=OPENAI_SEMANTIC_JUDGE_ID,
                judge_configuration=judge.provenance,
                case_ids=selected_ids,
            )
            semantic_path = stage / "semantic-evaluation.json"
            write_semantic_artifact(semantic, semantic_path)
            persisted = load_semantic_artifact(semantic_path, raw_run=raw_run)
            report = aggregate_semantic_report(
                raw_run,
                deterministic,
                persisted,
                human_labels=human_labels,
                guardrails=guardrails,
            )
            json_path = stage / "semantic-summary.json"
            markdown_path = stage / "semantic-report.md"
            write_semantic_report(report, json_path, markdown_path)
            validate_semantic_report(report, json_path, markdown_path)

        _publish_directory(args.output_directory, build_semantic)
        print(
            "Wrote semantic-evaluation.json, semantic-summary.json, and semantic-report.md "
            f"atomically to {args.output_directory}"
        )
        return 0

    if args.command == "report-semantic-calibration":
        raw_run = load_run_artifact(args.raw_run)
        deterministic = load_evaluation_artifact(args.deterministic_evaluation, raw_run=raw_run)
        semantic = load_semantic_artifact(args.semantic_evaluation, raw_run=raw_run)
        labels = load_human_labels(
            args.human_labels,
            raw_run=raw_run,
            case_ids=tuple(result.case_id for result in semantic.results),
        )
        disagreement_review = (
            None
            if args.disagreement_review is None
            else load_disagreement_review(
                args.disagreement_review,
                raw_run=raw_run,
                semantic=semantic,
                human=labels,
            )
        )

        def build_calibration_report(stage: Path) -> None:
            report = calibration_report(
                raw_run,
                deterministic,
                semantic,
                labels,
                disagreement_review,
            )
            json_path = stage / "calibration.json"
            markdown_path = stage / "calibration.md"
            write_calibration_report(report, json_path, markdown_path)
            validate_calibration_report(report, json_path, markdown_path)
            if disagreement_review is None:
                template = build_disagreement_review_template(raw_run, semantic, labels)
                write_disagreement_review_template(
                    template,
                    stage / "disagreement-review.draft.json",
                    stage / "disagreement-review.draft.md",
                )

        _publish_directory(args.output_directory, build_calibration_report)
        print(
            "Wrote reconciled calibration evidence and, when review evidence was not "
            f"supplied, a disagreement-review draft to {args.output_directory}"
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

    if args.command in {"run-guardrailed-replay", "run-openai-guardrailed"}:
        baseline_raw, baseline_evaluated = _load_baseline_bundle(args.baseline_directory)
        _validate_dataset_matches_baseline(args.dataset, baseline_raw)
        evidence_paths = _comparison_evidence_paths(
            args.baseline_directory,
            args.output_directory,
            repository_root=_find_repository_root(
                args.dataset, args.baseline_directory, Path.cwd()
            ),
        )

        if args.command == "run-guardrailed-replay":
            system: SystemUnderTest = _ReplaySystem(baseline_raw)
            system_id = f"{baseline_raw.system.id}-deterministic-replay-guardrailed"
            system_configuration = {
                **baseline_raw.system.configuration,
                "replay_source_run_id": baseline_raw.run_id,
                COMPARISON_MODE_CONFIGURATION_KEY: ComparisonMode.DETERMINISTIC_REPLAY.value,
                **guardrail_provenance(),
            }
        else:
            from llm_eval_guardrails.openai_adapter import (
                BASELINE_PROMPT_VERSION,
                CONTEXT_FORMAT_VERSION,
                OpenAIResponsesSystem,
                openai_provenance,
            )

            configuration = baseline_raw.system.configuration
            if configuration.get("provider") != "openai" or configuration.get("api") != "responses":
                raise ValueError("baseline is not an OpenAI Responses run")
            if configuration.get("prompt_version") != BASELINE_PROMPT_VERSION:
                raise ValueError("baseline prompt version is unavailable in this implementation")
            if configuration.get("context_format_version") != CONTEXT_FORMAT_VERSION:
                raise ValueError("baseline context-format version is unavailable")
            model = configuration.get("model")
            max_output_tokens = configuration.get("max_output_tokens")
            if not isinstance(model, str) or not model:
                raise ValueError("baseline model identifier is missing")
            if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
                raise ValueError("baseline maximum output tokens is invalid")
            openai_system = OpenAIResponsesSystem(
                model=model,
                max_output_tokens=max_output_tokens,
            )
            system = openai_system
            system_id = "openai-responses-northstar-guardrailed"
            system_configuration = {
                **openai_provenance(
                    model=model,
                    max_output_tokens=max_output_tokens,
                    sdk_version=openai_system.sdk_version,
                ),
                COMPARISON_MODE_CONFIGURATION_KEY: (ComparisonMode.FRESH_PROVIDER_EXECUTION.value),
                **guardrail_provenance(),
            }

        def build_guardrailed(stage: Path) -> None:
            _build_guardrailed_bundle(
                stage,
                dataset=args.dataset,
                system=system,
                system_id=system_id,
                system_configuration=system_configuration,
                run_id=args.run_id,
                baseline_raw=baseline_raw,
                baseline_evaluated=baseline_evaluated,
                evidence_paths=evidence_paths,
            )

        _publish_directory(args.output_directory, build_guardrailed)
        print(
            "Wrote raw-run.json, evaluated-run.json, summary.json, report.md, "
            "guardrail-decisions.json, comparison.json, and comparison.md atomically to "
            f"{args.output_directory}"
        )
        if args.command == "run-guardrailed-replay":
            print("This is deterministic replay plumbing evidence, not a new model measurement.")
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


def _load_baseline_bundle(directory: Path) -> tuple[RunArtifact, EvaluationArtifact]:
    raw = load_run_artifact(directory / "raw-run.json")
    evaluated = load_evaluation_artifact(directory / "evaluated-run.json", raw_run=raw)
    return raw, evaluated


def _validate_dataset_matches_baseline(dataset_path: Path, baseline: RunArtifact) -> None:
    cases = tuple(load_dataset(dataset_path))
    current = DatasetProvenance(str(dataset_path), cases)
    if current.fingerprint != baseline.dataset.fingerprint:
        raise ValueError("dataset fingerprint does not match the selected baseline")
    if tuple(case.id for case in current.cases) != tuple(
        case.id for case in baseline.dataset.cases
    ):
        raise ValueError("dataset ordered case IDs do not match the selected baseline")


def _build_guardrailed_bundle(
    stage: Path,
    *,
    dataset: Path,
    system: SystemUnderTest,
    system_id: str,
    system_configuration: Mapping[str, JsonValue],
    run_id: str | None,
    baseline_raw: RunArtifact,
    baseline_evaluated: EvaluationArtifact,
    evidence_paths: ComparisonEvidencePaths,
) -> None:
    raw, decisions = run_guardrailed_dataset(
        dataset,
        system,
        system_id=system_id,
        system_configuration=system_configuration,
        run_id=run_id,
    )
    raw_path = stage / "raw-run.json"
    evaluated_path = stage / "evaluated-run.json"
    decisions_path = stage / "guardrail-decisions.json"
    write_run_artifact(raw, raw_path)
    write_guardrail_artifact(decisions, decisions_path)
    persisted_raw = load_run_artifact(raw_path)
    persisted_decisions = load_guardrail_artifact(decisions_path, raw_run=persisted_raw)
    evaluated = evaluate_run(persisted_raw)
    write_evaluation_artifact(evaluated, evaluated_path)
    persisted_evaluated = load_evaluation_artifact(evaluated_path, raw_run=persisted_raw)
    report = aggregate_run(persisted_raw, persisted_evaluated)
    summary_path = stage / "summary.json"
    report_path = stage / "report.md"
    write_json_report(report, summary_path)
    write_markdown_report(report, report_path)
    validate_json_report(report, summary_path)
    validate_markdown_report(report, report_path)
    comparison = compare_runs(
        baseline_raw,
        baseline_evaluated,
        persisted_raw,
        persisted_evaluated,
        persisted_decisions,
        evidence_paths=evidence_paths,
    )
    comparison_path = stage / "comparison.json"
    comparison_markdown_path = stage / "comparison.md"
    write_comparison_artifact(comparison, comparison_path)
    write_comparison_markdown(comparison, comparison_markdown_path)
    validate_comparison_artifact(comparison, comparison_path)
    validate_comparison_markdown(comparison, comparison_markdown_path)


def _comparison_evidence_paths(
    baseline_directory: Path,
    output_directory: Path,
    *,
    repository_root: Path | None,
) -> ComparisonEvidencePaths:
    baseline_raw = (baseline_directory / "raw-run.json").resolve()
    baseline_evaluated = (baseline_directory / "evaluated-run.json").resolve()
    output = output_directory.resolve()

    if repository_root is not None:
        repository = repository_root.resolve()
        if baseline_raw.is_relative_to(repository) and baseline_evaluated.is_relative_to(
            repository
        ):
            return ComparisonEvidencePaths(
                baseline_raw=EvidenceReference(
                    baseline_raw.relative_to(repository).as_posix(),
                    EvidencePathBase.REPOSITORY_ROOT,
                ),
                baseline_evaluated=EvidenceReference(
                    baseline_evaluated.relative_to(repository).as_posix(),
                    EvidencePathBase.REPOSITORY_ROOT,
                ),
            )

    output_parent = output.parent
    if baseline_raw.is_relative_to(output_parent) and baseline_evaluated.is_relative_to(
        output_parent
    ):
        return ComparisonEvidencePaths(
            baseline_raw=EvidenceReference(
                Path(os.path.relpath(baseline_raw, output)).as_posix(),
                EvidencePathBase.COMPARISON_BUNDLE,
            ),
            baseline_evaluated=EvidenceReference(
                Path(os.path.relpath(baseline_evaluated, output)).as_posix(),
                EvidencePathBase.COMPARISON_BUNDLE,
            ),
        )

    raise ValueError(
        "baseline evidence is outside both the repository and the comparison bundle's "
        "parent; copy it into a stable repository or sibling-bundle location"
    )


def _find_repository_root(*paths: Path) -> Path | None:
    for path in paths:
        resolved = path.resolve()
        start = resolved if resolved.is_dir() else resolved.parent
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "PROJECT_STATE.md"
            ).is_file():
                return candidate
    return None


class _ReplaySystem:
    """Replay successful baseline outputs by request content, without case metadata."""

    def __init__(self, baseline: RunArtifact) -> None:
        self._responses: dict[tuple[str, tuple[str, ...]], SystemResponse | Exception] = {}
        for case, result in zip(baseline.dataset.cases, baseline.results, strict=True):
            key = (case.input, case.context)
            if key in self._responses:
                raise ValueError(
                    "baseline contains duplicate system requests and cannot be replayed"
                )
            if result.status is ExecutionStatus.SUCCESS:
                self._responses[key] = SystemResponse(result.output)
            else:
                self._responses[key] = RuntimeError("baseline replay source was an execution error")

    def invoke(self, request: SystemRequest, /) -> SystemResponse:
        response = self._responses.get((request.input, request.context))
        if response is None:
            raise ValueError("request is absent from the baseline replay source")
        if isinstance(response, Exception):
            raise response
        return response


if __name__ == "__main__":
    raise SystemExit(main())
