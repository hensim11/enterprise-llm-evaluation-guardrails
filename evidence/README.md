# Reviewed Evidence

This directory is reserved for deliberately selected, tracked, non-sensitive evidence from
authorized real experiments. Generated runs belong under the ignored `artifacts/` directory
until every raw case, evaluated result, aggregate, and metadata field has been inspected.

A retained baseline package uses:

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
