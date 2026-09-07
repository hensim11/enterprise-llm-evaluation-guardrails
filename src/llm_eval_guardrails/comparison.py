"""Matched baseline-to-guardrailed comparison evidence and rendering."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath

from llm_eval_guardrails.evaluation_artifact import EvaluationArtifact, EvaluationOutcome
from llm_eval_guardrails.guardrail_artifact import GuardrailDecisionArtifact
from llm_eval_guardrails.guardrails import GuardrailDecision
from llm_eval_guardrails.run_artifact import JsonValue, RunArtifact

COMPARISON_ARTIFACT_SCHEMA_VERSION = "1"
BENIGN_TAGS = frozenset({"benign", "benign_control"})
ADVERSARIAL_TAG = "adversarial"
COMPARISON_MODE_CONFIGURATION_KEY = "guardrail_comparison_mode"


class ComparisonMode(StrEnum):
    """How the guardrailed candidate responses were obtained."""

    DETERMINISTIC_REPLAY = "deterministic_replay"
    FRESH_PROVIDER_EXECUTION = "fresh_provider_execution"


class EvidencePathBase(StrEnum):
    """Stable base used to resolve a retained evidence reference."""

    COMPARISON_BUNDLE = "comparison_bundle"
    REPOSITORY_ROOT = "repository_root"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """A portable, explicitly based relative reference to evidence."""

    path: str
    base: EvidencePathBase

    def __post_init__(self) -> None:
        if not isinstance(self.base, EvidencePathBase):
            raise TypeError("evidence reference base must be an EvidencePathBase")
        if not isinstance(self.path, str) or not self.path:
            raise ValueError("evidence reference path must be a non-empty string")
        if "\\" in self.path or PurePosixPath(self.path).is_absolute():
            raise ValueError("evidence reference path must be relative POSIX text")
        if PureWindowsPath(self.path).is_absolute():
            raise ValueError("evidence reference path must not be an absolute Windows path")
        normalized = PurePosixPath(self.path)
        if self.path != normalized.as_posix() or normalized == PurePosixPath("."):
            raise ValueError("evidence reference path must be normalized relative POSIX text")
        if self.base is EvidencePathBase.REPOSITORY_ROOT and ".." in normalized.parts:
            raise ValueError("repository-root evidence references must stay within the repository")

    def to_mapping(self) -> dict[str, JsonValue]:
        return {"base": self.base.value, "path": self.path}

    def resolve(self, *, comparison_bundle: Path, repository_root: Path) -> Path:
        base = {
            EvidencePathBase.COMPARISON_BUNDLE: comparison_bundle,
            EvidencePathBase.REPOSITORY_ROOT: repository_root,
        }[self.base]
        resolved_base = base.resolve()
        resolved = (resolved_base / self.path).resolve()
        allowed_root = (
            resolved_base.parent
            if self.base is EvidencePathBase.COMPARISON_BUNDLE
            else resolved_base
        )
        if not resolved.is_relative_to(allowed_root):
            raise ValueError("evidence reference resolves outside its allowed base boundary")
        return resolved


@dataclass(frozen=True, slots=True)
class ComparisonEvidencePaths:
    baseline_raw: EvidenceReference
    baseline_evaluated: EvidenceReference
    guardrailed_raw: EvidenceReference = EvidenceReference(
        "raw-run.json", EvidencePathBase.COMPARISON_BUNDLE
    )
    guardrailed_evaluated: EvidenceReference = EvidenceReference(
        "evaluated-run.json", EvidencePathBase.COMPARISON_BUNDLE
    )
    guardrail_decisions: EvidenceReference = EvidenceReference(
        "guardrail-decisions.json", EvidencePathBase.COMPARISON_BUNDLE
    )

    def __post_init__(self) -> None:
        for name in (
            "baseline_raw",
            "baseline_evaluated",
            "guardrailed_raw",
            "guardrailed_evaluated",
            "guardrail_decisions",
        ):
            if not isinstance(getattr(self, name), EvidenceReference):
                raise TypeError(f"{name} must be an EvidenceReference")


@dataclass(frozen=True, slots=True)
class GuardrailComparison:
    """Canonical comparison over five exactly joined source artefacts."""

    baseline_raw: RunArtifact
    baseline_evaluated: EvaluationArtifact
    guardrailed_raw: RunArtifact
    guardrailed_evaluated: EvaluationArtifact
    guardrail_decisions: GuardrailDecisionArtifact
    evidence_paths: ComparisonEvidencePaths

    def __post_init__(self) -> None:
        self.baseline_evaluated.validate_against(self.baseline_raw)
        self.guardrailed_evaluated.validate_against(self.guardrailed_raw)
        self.guardrail_decisions.validate_against(self.guardrailed_raw)
        if self.baseline_raw.dataset.fingerprint != self.guardrailed_raw.dataset.fingerprint:
            raise ValueError("baseline and guardrailed dataset fingerprints must match exactly")
        baseline_ids = tuple(case.id for case in self.baseline_raw.dataset.cases)
        guardrailed_ids = tuple(case.id for case in self.guardrailed_raw.dataset.cases)
        if baseline_ids != guardrailed_ids:
            raise ValueError("baseline and guardrailed ordered case IDs must match exactly")
        _comparison_mode(self.baseline_raw, self.guardrailed_raw)
        for case in self.baseline_raw.dataset.cases:
            tags = set(case.tags)
            if tags & BENIGN_TAGS and ADVERSARIAL_TAG in tags:
                raise ValueError(f"case {case.id!r} has conflicting benign/adversarial labels")

    def to_mapping(self) -> dict[str, JsonValue]:
        mode = _comparison_mode(self.baseline_raw, self.guardrailed_raw)
        baseline_cases = self.baseline_raw.dataset.cases
        case_rows = list(
            zip(
                baseline_cases,
                self.baseline_raw.results,
                self.baseline_evaluated.results,
                self.guardrailed_raw.results,
                self.guardrailed_evaluated.results,
                self.guardrail_decisions.decisions,
                strict=True,
            )
        )
        baseline_counts = _evaluation_counts(self.baseline_evaluated)
        guardrailed_counts = _evaluation_counts(self.guardrailed_evaluated)
        decision_counts = Counter(
            decision.final_decision.value for decision in self.guardrail_decisions.decisions
        )
        trigger_counts = Counter(
            (trigger.detector_id, trigger.version, trigger.stage.value)
            for decision in self.guardrail_decisions.decisions
            for trigger in decision.triggered_detectors
        )
        classifications = [_classification(case.tags) for case in baseline_cases]
        benign_indices = [
            index
            for index, classification in enumerate(classifications)
            if classification == "benign"
        ]
        adversarial_indices = [
            index
            for index, classification in enumerate(classifications)
            if classification == "adversarial"
        ]
        unclassified_indices = [
            index
            for index, classification in enumerate(classifications)
            if classification == "unclassified"
        ]
        benign_blocks = [
            baseline_cases[index].id
            for index in benign_indices
            if self.guardrail_decisions.decisions[index].final_decision is GuardrailDecision.BLOCK
        ]
        benign_warnings = [
            baseline_cases[index].id
            for index in benign_indices
            if self.guardrail_decisions.decisions[index].final_decision is GuardrailDecision.WARN
        ]
        adversarial_counts = Counter(
            self.guardrail_decisions.decisions[index].final_decision.value
            for index in adversarial_indices
        )
        transitions = Counter(
            (baseline.outcome.value, guardrailed.outcome.value)
            for _, _, baseline, _, guardrailed, _ in case_rows
        )

        trace: list[JsonValue] = []
        for index, (
            case,
            baseline_raw,
            baseline_eval,
            guarded_raw,
            guarded_eval,
            decision,
        ) in enumerate(case_rows):
            trace.append(
                {
                    "case_id": case.id,
                    "classification": classifications[index],
                    "baseline": {
                        "raw_result_index": index,
                        "evaluated_result_index": index,
                        "execution_status": baseline_raw.status.value,
                        "case_outcome": baseline_eval.outcome.value,
                        "assertion_outcomes": [
                            assertion.outcome.value for assertion in baseline_eval.assertions
                        ],
                    },
                    "guardrailed": {
                        "raw_result_index": index,
                        "evaluated_result_index": index,
                        "decision_index": index,
                        "execution_status": guarded_raw.status.value,
                        "case_outcome": guarded_eval.outcome.value,
                        "assertion_outcomes": [
                            assertion.outcome.value for assertion in guarded_eval.assertions
                        ],
                        "decision": decision.final_decision.value,
                        "triggered_detectors": [
                            {
                                "id": trigger.detector_id,
                                "version": trigger.version,
                                "stage": trigger.stage.value,
                            }
                            for trigger in decision.triggered_detectors
                        ],
                        "underlying_model_invoked": decision.underlying_model_invoked,
                        "candidate_response_released": decision.candidate_response_released,
                        "candidate_response_replaced": decision.candidate_response_replaced,
                    },
                    "outcome_transition": (
                        f"{baseline_eval.outcome.value}->{guarded_eval.outcome.value}"
                    ),
                }
            )

        return {
            "schema_version": COMPARISON_ARTIFACT_SCHEMA_VERSION,
            "comparison_mode": mode.value,
            "attribution": _attribution_mapping(mode),
            "source": {
                "baseline": _source_mapping(
                    self.baseline_raw,
                    self.evidence_paths.baseline_raw,
                    self.evidence_paths.baseline_evaluated,
                ),
                "guardrailed": {
                    **_source_mapping(
                        self.guardrailed_raw,
                        self.evidence_paths.guardrailed_raw,
                        self.evidence_paths.guardrailed_evaluated,
                    ),
                    "guardrail_decisions": self.evidence_paths.guardrail_decisions.to_mapping(),
                    "policy": {
                        "id": self.guardrail_decisions.policy_id,
                        "version": self.guardrail_decisions.policy_version,
                    },
                },
            },
            "matched_cases": {
                "count": len(baseline_cases),
                "ordered_case_ids": [case.id for case in baseline_cases],
            },
            "system_configuration_differences": _configuration_differences(
                self.baseline_raw, self.guardrailed_raw
            ),
            "guardrails": {
                "decision_counts": {
                    decision.value: decision_counts[decision.value]
                    for decision in GuardrailDecision
                },
                "detector_trigger_counts": [
                    {
                        "id": detector.detector_id,
                        "version": detector.version,
                        "stage": detector.stage.value,
                        "count": trigger_counts[
                            (detector.detector_id, detector.version, detector.stage.value)
                        ],
                    }
                    for detector in self.guardrail_decisions.detector_versions
                ],
                "underlying_model_invocations_avoided": sum(
                    not decision.underlying_model_invoked
                    for decision in self.guardrail_decisions.decisions
                ),
            },
            "deterministic_deltas": {
                "baseline": baseline_counts,
                "guardrailed": guardrailed_counts,
                "case_outcome_delta": _delta(
                    baseline_counts["case_outcomes"], guardrailed_counts["case_outcomes"]
                ),
                "assertion_outcome_delta": _delta(
                    baseline_counts["assertion_outcomes"],
                    guardrailed_counts["assertion_outcomes"],
                ),
                "baseline_to_guardrailed_outcome_transitions": [
                    {"from": before, "to": after, "count": count}
                    for (before, after), count in sorted(transitions.items())
                ],
            },
            "classification": {
                "benign": {
                    "all_benign_labelled_cases": len(benign_indices),
                    "false_refusals": {
                        **_rate(len(benign_blocks), len(benign_indices)),
                        "case_ids": benign_blocks,
                    },
                    "warnings": {
                        **_rate(len(benign_warnings), len(benign_indices)),
                        "case_ids": benign_warnings,
                    },
                },
                "adversarial": {
                    "all_adversarial_labelled_cases": len(adversarial_indices),
                    "decisions": {
                        decision.value: adversarial_counts[decision.value]
                        for decision in GuardrailDecision
                    },
                },
                "unclassified": {
                    "count": len(unclassified_indices),
                    "case_ids": [baseline_cases[index].id for index in unclassified_indices],
                },
            },
            "case_trace": trace,
        }


def compare_runs(
    baseline_raw: RunArtifact,
    baseline_evaluated: EvaluationArtifact,
    guardrailed_raw: RunArtifact,
    guardrailed_evaluated: EvaluationArtifact,
    guardrail_decisions: GuardrailDecisionArtifact,
    *,
    evidence_paths: ComparisonEvidencePaths,
) -> GuardrailComparison:
    return GuardrailComparison(
        baseline_raw,
        baseline_evaluated,
        guardrailed_raw,
        guardrailed_evaluated,
        guardrail_decisions,
        evidence_paths,
    )


def write_comparison_artifact(report: GuardrailComparison, path: str | Path) -> None:
    serialized = json.dumps(report.to_mapping(), ensure_ascii=False, allow_nan=False, indent=2)
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(serialized + "\n")


def validate_comparison_artifact(report: GuardrailComparison, path: str | Path) -> None:
    value = _load_json(path)
    if value != report.to_mapping():
        raise ValueError("comparison artefact does not match canonical recomputation")


def load_comparison_artifact(
    path: str | Path,
    *,
    baseline_raw: RunArtifact,
    baseline_evaluated: EvaluationArtifact,
    guardrailed_raw: RunArtifact,
    guardrailed_evaluated: EvaluationArtifact,
    guardrail_decisions: GuardrailDecisionArtifact,
    evidence_paths: ComparisonEvidencePaths,
) -> GuardrailComparison:
    """Load by requiring exact equality with a canonical matched-run recomputation."""
    report = compare_runs(
        baseline_raw,
        baseline_evaluated,
        guardrailed_raw,
        guardrailed_evaluated,
        guardrail_decisions,
        evidence_paths=evidence_paths,
    )
    validate_comparison_artifact(report, path)
    return report


def render_comparison_markdown(report: GuardrailComparison) -> str:
    value = report.to_mapping()
    mode = ComparisonMode(value["comparison_mode"])
    attribution = value["attribution"]
    source = value["source"]
    guardrails = value["guardrails"]
    deltas = value["deterministic_deltas"]
    classification = value["classification"]
    benign = classification["benign"]
    title = {
        ComparisonMode.DETERMINISTIC_REPLAY: "# Deterministic Replay Guardrail Comparison",
        ComparisonMode.FRESH_PROVIDER_EXECUTION: (
            "# Fresh-Provider Guardrail Comparison (Observational)"
        ),
    }[mode]
    lines = [
        title,
        "",
        f"- Comparison mode: `{mode.value}`",
        f"- Baseline run: `{_md(source['baseline']['run_id'])}`",
        f"- Baseline system: `{_md(source['baseline']['system']['id'])}`",
        "- Baseline configuration: "
        f"`{_md(_compact(source['baseline']['system']['configuration']))}`",
        f"- Baseline raw evidence: `{_md(_reference_text(source['baseline']['raw_evidence']))}`",
        "- Baseline evaluated evidence: "
        f"`{_md(_reference_text(source['baseline']['evaluated_evidence']))}`",
        f"- Guardrailed run: `{_md(source['guardrailed']['run_id'])}`",
        f"- Guardrailed system: `{_md(source['guardrailed']['system']['id'])}`",
        "- Guardrailed configuration: "
        f"`{_md(_compact(source['guardrailed']['system']['configuration']))}`",
        "- Guardrailed raw evidence: "
        f"`{_md(_reference_text(source['guardrailed']['raw_evidence']))}`",
        "- Guardrailed evaluated evidence: "
        f"`{_md(_reference_text(source['guardrailed']['evaluated_evidence']))}`",
        "- Guardrail decision evidence: "
        f"`{_md(_reference_text(source['guardrailed']['guardrail_decisions']))}`",
        f"- Dataset fingerprint: `{_md(source['baseline']['dataset_fingerprint'])}`",
        f"- Policy: `{_md(source['guardrailed']['policy']['id'])}` version "
        f"`{_md(source['guardrailed']['policy']['version'])}`",
        "",
        "## Attribution basis",
        "",
        str(attribution["summary"]),
        "",
        f"- Input-block avoidance: {attribution['input_block_avoidance']['explanation']}",
        "- PASS/WARN candidate-response comparison: "
        f"{attribution['pass_warn_candidate_responses']['explanation']}",
        f"- Evaluation deltas and transitions: {attribution['evaluation_deltas']['explanation']}",
        "",
        "## Guardrail decisions",
        "",
        (
            "- Pass / warn / block: "
            f"{guardrails['decision_counts']['pass']} / "
            f"{guardrails['decision_counts']['warn']} / "
            f"{guardrails['decision_counts']['block']}"
        ),
        "- Underlying model invocations avoided: "
        f"{guardrails['underlying_model_invocations_avoided']}",
        "",
        "| Detector | Version | Stage | Triggers |",
        "| --- | --- | --- | ---: |",
    ]
    for trigger in guardrails["detector_trigger_counts"]:
        lines.append(
            f"| {_md(trigger['id'])} | {_md(trigger['version'])} | "
            f"{_md(trigger['stage'])} | {trigger['count']} |"
        )
    lines.extend(
        [
            "",
            "## Deterministic evaluation comparison",
            "",
            "| Outcome | Baseline cases | Guardrailed cases | Delta |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for outcome in EvaluationOutcome:
        name = outcome.value
        lines.append(
            f"| {name} | {deltas['baseline']['case_outcomes'][name]} | "
            f"{deltas['guardrailed']['case_outcomes'][name]} | "
            f"{deltas['case_outcome_delta'][name]} |"
        )
    lines.extend(
        [
            "",
            "Assertion outcome delta (guardrailed minus baseline): "
            + ", ".join(
                f"{name} {change:+d}" for name, change in deltas["assertion_outcome_delta"].items()
            )
            + ".",
            "",
            "## Labelled-case policy observations",
            "",
            "- False refusals (guardrail blocks on `benign` or `benign_control`): "
            f"{_rate_text(benign['false_refusals'])}",
            f"- Warnings on benign cases: {_rate_text(benign['warnings'])}",
            "- Adversarial block / warn / pass: "
            f"{classification['adversarial']['decisions']['block']} / "
            f"{classification['adversarial']['decisions']['warn']} / "
            f"{classification['adversarial']['decisions']['pass']}",
            "- Cases without benign/adversarial classification: "
            f"{classification['unclassified']['count']} "
            f"({', '.join(classification['unclassified']['case_ids']) or 'none'})",
            "",
            "The adversarial counts are policy decisions, not an accuracy score. WARN is not "
            "a refusal, and model wording is not used to infer refusal.",
            "",
            "## System configuration differences",
            "",
            "| Field | Baseline | Guardrailed |",
            "| --- | --- | --- |",
        ]
    )
    for difference in value["system_configuration_differences"]:
        lines.append(
            f"| {_md(difference['field'])} | {_md(_compact(difference['baseline']))} | "
            f"{_md(_compact(difference['guardrailed']))} |"
        )
    lines.extend(
        [
            "",
            "## Complete case trace",
            "",
            "| Case | Class | Baseline | Guardrailed | Transition | Decision | Invoked | "
            "Released | Replaced | Triggers |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for trace in value["case_trace"]:
        guarded = trace["guardrailed"]
        trigger_text = (
            ", ".join(f"{item['id']}@{item['stage']}" for item in guarded["triggered_detectors"])
            or "none"
        )
        lines.append(
            f"| {_md(trace['case_id'])} | {trace['classification']} | "
            f"{trace['baseline']['case_outcome']} | {guarded['case_outcome']} | "
            f"{trace['outcome_transition']} | {guarded['decision']} | "
            f"{str(guarded['underlying_model_invoked']).lower()} | "
            f"{str(guarded['candidate_response_released']).lower()} | "
            f"{str(guarded['candidate_response_replaced']).lower()} | {_md(trigger_text)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "Detector results are narrow phrase and pattern matches, not semantic understanding "
            "or a security guarantee. Deterministic outcome changes reflect only configured "
            "literal assertions. No composite safety score is calculated.",
            "",
        ]
    )
    return "\n".join(lines)


def write_comparison_markdown(report: GuardrailComparison, path: str | Path) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write(render_comparison_markdown(report))


def validate_comparison_markdown(report: GuardrailComparison, path: str | Path) -> None:
    if Path(path).read_text(encoding="utf-8") != render_comparison_markdown(report):
        raise ValueError("comparison Markdown does not match canonical rendering")


def _source_mapping(
    raw: RunArtifact,
    raw_path: EvidenceReference,
    evaluated_path: EvidenceReference,
) -> dict[str, JsonValue]:
    return {
        "run_id": raw.run_id,
        "dataset_fingerprint": raw.dataset.fingerprint,
        "system": raw.system.to_mapping(),
        "raw_evidence": raw_path.to_mapping(),
        "evaluated_evidence": evaluated_path.to_mapping(),
    }


def _comparison_mode(baseline: RunArtifact, guardrailed: RunArtifact) -> ComparisonMode:
    configured = guardrailed.system.configuration.get(COMPARISON_MODE_CONFIGURATION_KEY)
    try:
        mode = ComparisonMode(configured)
    except (TypeError, ValueError) as error:
        raise ValueError("guardrailed run has no supported comparison mode") from error

    replay_source_run_id = guardrailed.system.configuration.get("replay_source_run_id")
    derived = (
        ComparisonMode.DETERMINISTIC_REPLAY
        if replay_source_run_id is not None
        else ComparisonMode.FRESH_PROVIDER_EXECUTION
    )
    if mode is not derived:
        raise ValueError("comparison mode conflicts with guardrailed execution provenance")
    if mode is ComparisonMode.DETERMINISTIC_REPLAY and replay_source_run_id != baseline.run_id:
        raise ValueError("deterministic replay source run ID must match the baseline run")
    return mode


def _attribution_mapping(mode: ComparisonMode) -> dict[str, JsonValue]:
    input_explanation = {
        ComparisonMode.DETERMINISTIC_REPLAY: (
            "The recorded avoided invocation follows directly from an input-stage BLOCK: "
            "the replay system was not invoked."
        ),
        ComparisonMode.FRESH_PROVIDER_EXECUTION: (
            "The recorded avoided provider invocation follows directly from an input-stage "
            "BLOCK: the provider-backed system was not invoked."
        ),
    }[mode]
    input_block = {
        "basis": "directly_attributable_to_input_guardrail",
        "explanation": input_explanation,
    }
    if mode is ComparisonMode.DETERMINISTIC_REPLAY:
        return {
            "summary": (
                "This mode reuses the retained baseline candidate responses for requests that "
                "reach the system. With the same retained candidate responses, differences are "
                "attributable to guardrail and deterministic evaluation treatment."
            ),
            "input_block_avoidance": input_block,
            "pass_warn_candidate_responses": {
                "basis": "same_retained_candidate_responses",
                "explanation": (
                    "PASS and WARN requests reuse the retained baseline candidate responses; "
                    "no new provider response was sampled."
                ),
            },
            "evaluation_deltas": {
                "basis": "attributable_to_guardrail_and_evaluation_treatment",
                "explanation": (
                    "Case and assertion deltas and transitions compare deterministic evaluation "
                    "of the baseline evidence with guardrail treatment of the same candidates."
                ),
            },
        }
    return {
        "summary": (
            "This mode samples fresh provider responses. Apart from input-block avoidance, "
            "observed differences are not necessarily guardrail-caused because provider or "
            "model nondeterminism may contribute."
        ),
        "input_block_avoidance": input_block,
        "pass_warn_candidate_responses": {
            "basis": "observational_confounded_by_provider_model_nondeterminism",
            "explanation": (
                "PASS and WARN outputs are fresh observations and may differ because of provider "
                "or model nondeterminism; their transitions are observational and confounded."
            ),
        },
        "evaluation_deltas": {
            "basis": "observational_not_necessarily_guardrail_caused",
            "explanation": (
                "The calculations are deterministic over their artefacts, but their deltas and "
                "transitions are not necessarily caused by guardrails."
            ),
        },
    }


def _evaluation_counts(artifact: EvaluationArtifact) -> dict[str, JsonValue]:
    cases = Counter(result.outcome.value for result in artifact.results)
    assertions = Counter(
        assertion.outcome.value for result in artifact.results for assertion in result.assertions
    )
    return {
        "case_outcomes": {outcome.value: cases[outcome.value] for outcome in EvaluationOutcome},
        "assertion_outcomes": {
            outcome.value: assertions[outcome.value]
            for outcome in (
                EvaluationOutcome.PASS,
                EvaluationOutcome.FAIL,
                EvaluationOutcome.ERROR,
            )
        },
    }


def _delta(before: Mapping[str, JsonValue], after: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: int(after[key]) - int(before[key]) for key in before}


def _classification(tags: tuple[str, ...]) -> str:
    tag_set = set(tags)
    if tag_set & BENIGN_TAGS:
        return "benign"
    if ADVERSARIAL_TAG in tag_set:
        return "adversarial"
    return "unclassified"


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


def _configuration_differences(baseline: RunArtifact, guardrailed: RunArtifact) -> list[JsonValue]:
    before = baseline.system.configuration
    after = guardrailed.system.configuration
    differences: list[JsonValue] = []
    for field in sorted(before.keys() | after.keys()):
        if field not in before or field not in after or before[field] != after[field]:
            differences.append(
                {
                    "field": field,
                    "baseline_present": field in before,
                    "guardrailed_present": field in after,
                    "baseline": before.get(field),
                    "guardrailed": after.get(field),
                }
            )
    if baseline.system.id != guardrailed.system.id:
        differences.insert(
            0,
            {
                "field": "system.id",
                "baseline_present": True,
                "guardrailed_present": True,
                "baseline": baseline.system.id,
                "guardrailed": guardrailed.system.id,
            },
        )
    return differences


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reference_text(reference: Mapping[str, JsonValue]) -> str:
    return f"{reference['base']}:{reference['path']}"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("`", "\\`")


def _load_json(path: str | Path) -> object:
    with Path(path).open("r", encoding="utf-8") as source:
        return json.load(source, object_pairs_hook=_unique_object, parse_constant=_reject_number)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")
