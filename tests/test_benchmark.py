from collections import Counter
from pathlib import Path

from llm_eval_guardrails import AssertionType, load_dataset

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "northstar_bank_v1.jsonl"


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
