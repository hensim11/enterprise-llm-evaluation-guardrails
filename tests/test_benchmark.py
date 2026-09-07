import json
from collections import Counter
from pathlib import Path

from llm_eval_guardrails import (
    AssertionType,
    DatasetProvenance,
    EchoSystemUnderTest,
    load_dataset,
    run_guardrailed_dataset,
)
from llm_eval_guardrails.cli import main

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "northstar_bank_v1.jsonl"
EXPECTED_FINGERPRINT = "6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698"
RETAINED_BASELINE = (
    ROOT / "evidence" / "baselines" / "northstar-v1-gpt-5.4-mini-2026-03-17-20260905"
)


def test_benchmark_has_stable_unique_fictional_cases_and_assertions() -> None:
    cases = load_dataset(BENCHMARK)

    assert len(cases) == 36
    assert len({case.id for case in cases}) == 36
    assert cases[0].id == "support-card-arrival-window"
    assert cases[-1].id == "control-context-official-colour"
    assert all(case.metadata["fictional"] is True for case in cases)
    assert all(case.metadata["benchmark"] == "northstar-bank-v1" for case in cases)
    assert all(case.expected_behavior for case in cases)
    assert {assertion.type for case in cases for assertion in case.assertions} == set(AssertionType)
    assert any(not case.assertions for case in cases)
    assert DatasetProvenance(str(BENCHMARK), tuple(cases)).fingerprint == EXPECTED_FINGERPRINT


def test_benchmark_covers_required_scenarios_and_risk_categories() -> None:
    cases = load_dataset(BENCHMARK)
    scenario_counts = Counter(case.metadata["scenario"] for case in cases)
    tags = {tag for case in cases for tag in case.tags}
    categories = {case.risk_category.value for case in cases if case.risk_category is not None}

    assert scenario_counts["ordinary_support"] == 6
    assert scenario_counts["grounded_policy"] == 6
    assert scenario_counts["hallucination_trap"] == 5
    assert scenario_counts["financial_boundary"] == 4
    assert scenario_counts["financial_boundary_control"] == 1
    assert scenario_counts["privacy"] == 4
    assert scenario_counts["privacy_control"] == 1
    assert scenario_counts["injection"] == 5
    assert scenario_counts["benign_control"] == 4
    assert {"adversarial", "benign_control", "paired_control"} <= tags
    assert {"groundedness", "privacy", "injection_resistance", "refusal_behavior"} <= categories


def test_adversarial_scenarios_have_benign_paired_controls() -> None:
    cases = load_dataset(BENCHMARK)
    pairs: dict[str, list[object]] = {}
    for case in cases:
        pair = case.metadata.get("pair")
        if isinstance(pair, str):
            pairs.setdefault(pair, []).append(case)

    assert pairs
    for pair, members in pairs.items():
        assert any("adversarial" in case.tags for case in members), pair
        assert any("benign_control" in case.tags for case in members), pair


def test_benchmark_contains_no_real_customer_or_bank_framing() -> None:
    text = BENCHMARK.read_text(encoding="utf-8")

    assert "Northstar" in text
    assert '"fictional":true' in text
    for prohibited in ("Barclays", "HSBC", "NatWest", "Santander", "real customer"):
        assert prohibited not in text


def test_guardrails_produce_one_explainable_decision_per_unchanged_benchmark_case() -> None:
    raw, decisions = run_guardrailed_dataset(
        BENCHMARK,
        EchoSystemUnderTest(),
        system_id="synthetic-echo-guardrailed",
        run_id="benchmark-guardrail-test",
    )

    assert raw.dataset.fingerprint == EXPECTED_FINGERPRINT
    assert len(raw.results) == len(decisions.decisions) == 36
    assert [result.case_id for result in raw.results] == [
        decision.case_id for decision in decisions.decisions
    ]
    assert sum(not decision.underlying_model_invoked for decision in decisions.decisions) == 9
    assert sum(decision.candidate_response_replaced for decision in decisions.decisions) == 1
    assert all(decision.explanation for decision in decisions.decisions)


def test_retained_baseline_replay_preserves_verified_comparison_metrics(tmp_path: Path) -> None:
    output = tmp_path / "replay"

    assert (
        main(
            [
                "run-guardrailed-replay",
                str(BENCHMARK),
                str(RETAINED_BASELINE),
                str(output),
                "--run-id",
                "verified-replay-test",
            ]
        )
        == 0
    )

    comparison = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert comparison["source"]["baseline"]["dataset_fingerprint"] == EXPECTED_FINGERPRINT
    assert comparison["matched_cases"]["count"] == 36
    assert comparison["guardrails"]["decision_counts"] == {
        "pass": 24,
        "warn": 3,
        "block": 9,
    }
    assert comparison["guardrails"]["underlying_model_invocations_avoided"] == 9
    assert comparison["deterministic_deltas"]["baseline"]["case_outcomes"] == {
        "pass": 29,
        "fail": 2,
        "error": 0,
        "not_applicable": 5,
    }
    assert comparison["deterministic_deltas"]["guardrailed"]["case_outcomes"] == {
        "pass": 28,
        "fail": 3,
        "error": 0,
        "not_applicable": 5,
    }
    assert comparison["deterministic_deltas"]["assertion_outcome_delta"] == {
        "pass": -1,
        "fail": 1,
        "error": 0,
    }
    assert comparison["classification"]["benign"]["false_refusals"]["denominator"] == 18
    assert comparison["classification"]["benign"]["false_refusals"]["numerator"] == 0
