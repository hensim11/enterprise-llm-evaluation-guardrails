# Reviewed Evidence

This directory is reserved for deliberately selected, tracked, non-sensitive evidence from
authorized real experiments. Generated runs belong under the ignored `artifacts/` directory
until every raw case, evaluated result, aggregate, and metadata field has been inspected.

Package layouts are capability-specific. A retained baseline package uses:

```text
evidence/baselines/<run-id>/
  raw-run.json
  evaluated-run.json
  summary.json
  report.md
```

The four files must come from one atomically generated bundle. Before adding them, verify
their run ID, dataset fingerprint, ordered joins, aggregate reconciliation, credential and
private-data screening, and model/prompt provenance. Do not hand-edit a retained metric or
publish synthetic echo/fake-client output here.

## Retained Batch A baseline

The accepted empirical package is
[`baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/`](baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/).

- `raw-run.json` contains 36 ordered successful executions and the complete benchmark
  snapshot.
- `evaluated-run.json` contains 36 ordered deterministic case results canonically derived
  from that raw run.
- `summary.json` contains the machine-readable aggregate and case traceability.
- `report.md` renders the same aggregate for human review.

The validation chain is:

```text
benchmark → raw run → deterministic evaluation → JSON/Markdown reports
```

The run identity is `northstar-v1-gpt-5.4-mini-2026-03-17-20260905`; it used model snapshot
`gpt-5.4-mini-2026-03-17`, SDK 1.66.0, and dataset fingerprint
`6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698`.
All joins and both report renderings validate canonically. The result includes 38 literal
assertions, of which 36 passed and two failed; 31 of 36 cases have deterministic assertion
coverage and five remain semantically unassessed.

These files record one finite run and narrow literal measurements, not proof of semantic
correctness, safety, privacy, prompt-injection robustness, or production readiness. They do
not contain provider token-usage metadata, so actual cost cannot be reconstructed from this
package.

## Retained Batch B guardrail comparison

The accepted empirical package is
[`guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/`](guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/).
It is a distinct seven-file layout:

```text
evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/
  raw-run.json                 externally observed outputs and run configuration
  evaluated-run.json           deterministic case and assertion evidence
  summary.json                 machine-readable ordinary evaluation aggregate
  report.md                    human-readable ordinary evaluation report
  guardrail-decisions.json     per-case enforcement and invocation evidence
  comparison.json              machine-readable matched baseline comparison
  comparison.md                human-readable observational comparison
```

The validation chain is:

```text
unchanged benchmark ──> raw-run.json ──> evaluated-run.json ──> summary.json + report.md
                         │
                         └─> guardrail-decisions.json

retained Batch A raw/evaluated evidence + all Batch B evidence
                         └─> comparison.json + comparison.md
```

`raw-run.json` identifies OpenAI Responses, model snapshot
`gpt-5.4-mini-2026-03-17`, prompt/context versions, the 36 ordered cases, and fingerprint
`6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698`.
The decision evidence records 27 successful provider invocations and nine input blocks that
directly avoided invocation. The comparison contains 36 ordered trace rows, declares
`fresh_provider_execution`, and uses portable `{base, path}` references: guardrailed files
resolve from `comparison_bundle`, while baseline files resolve from `repository_root`.

The empirical decisions were 24 PASS, 3 WARN, and 9 BLOCK. The guardrailed run passed 35 of
38 literal assertions versus 36 of 38 for the baseline. The only case/assertion transition
was `unsupported-mortgage-eligibility`, pass → fail. Twenty-one of 27 released provider
outputs differed textually from the baseline. Input-block avoidance is directly
attributable to enforcement; fresh PASS/WARN output differences and resulting metrics are
observational and potentially confounded by provider/model nondeterminism. BLOCK counts are
policy observations, not semantic correctness or safety scores.

### Reconcile the retained bundle

From the repository root after installing the package, this uses the public canonical
loaders and render validators. It makes no provider request:

```bash
python - <<'PY'
from pathlib import Path

from llm_eval_guardrails import (
    ComparisonEvidencePaths,
    EvidencePathBase,
    EvidenceReference,
    aggregate_run,
    load_comparison_artifact,
    load_evaluation_artifact,
    load_guardrail_artifact,
    load_run_artifact,
    validate_comparison_markdown,
    validate_json_report,
    validate_markdown_report,
)

root = Path.cwd()
baseline = root / "evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905"
bundle = root / "evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906"

baseline_raw = load_run_artifact(baseline / "raw-run.json")
baseline_evaluated = load_evaluation_artifact(
    baseline / "evaluated-run.json", raw_run=baseline_raw
)
raw = load_run_artifact(bundle / "raw-run.json")
evaluated = load_evaluation_artifact(bundle / "evaluated-run.json", raw_run=raw)
decisions = load_guardrail_artifact(bundle / "guardrail-decisions.json", raw_run=raw)
paths = ComparisonEvidencePaths(
    EvidenceReference(
        "evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/raw-run.json",
        EvidencePathBase.REPOSITORY_ROOT,
    ),
    EvidenceReference(
        "evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/evaluated-run.json",
        EvidencePathBase.REPOSITORY_ROOT,
    ),
)
comparison = load_comparison_artifact(
    bundle / "comparison.json",
    baseline_raw=baseline_raw,
    baseline_evaluated=baseline_evaluated,
    guardrailed_raw=raw,
    guardrailed_evaluated=evaluated,
    guardrail_decisions=decisions,
    evidence_paths=paths,
)
validate_comparison_markdown(comparison, bundle / "comparison.md")
report = aggregate_run(raw, evaluated)
validate_json_report(report, bundle / "summary.json")
validate_markdown_report(report, bundle / "report.md")
print("Batch B retained evidence reconciles canonically.")
PY
```

Reviewers should additionally inspect every raw output, decision, case transition, and
comparison attribution statement. The full case snapshot intentionally contains fictional
PIN/card/canary test values; released provider outputs contain no detected synthetic-secret
leakage. No real customer data, credential, machine-specific path, or provider usage/cost
metadata is retained.
