# Batch B Guardrail Impact Workflow

## Evidence flow

```text
unchanged cases -> request-only input checks --BLOCK--> versioned observed output
                         | PASS/WARN
                         v
                 underlying system -> candidate response checks
                                      | PASS             | BLOCK
                                      v                  v
                              observed raw output   versioned replacement

raw-run.json -----------------------> evaluated-run.json -> summary.json + report.md
guardrail-decisions.json --------------------------------> comparison.json + comparison.md
retained baseline raw/evaluated evidence ------------------------------^
```

The raw and evaluated schemas are reused unchanged. Runtime policy data appears only in
system configuration provenance and the dedicated decision/comparison artefacts.

## Offline deterministic replay

This command replays the retained successful Batch A outputs by request content, applies
the guardrails, and emits the complete seven-file bundle atomically without credentials or
network access:

```bash
python -m llm_eval_guardrails run-guardrailed-replay \
  benchmarks/northstar_bank_v1.jsonl \
  evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905 \
  /path/to/new-replay-bundle \
  --run-id RUN_ID
```

Replay is deterministic plumbing and policy-impact evidence over retained responses. It is
not a new model invocation or a measurement of how a fresh provider response would interact
with response checks. Input-block invocation avoidance is demonstrated against the replay
double, and separate tests use a deliberately leaking fake system to demonstrate response
blocking.

The emitted comparison mode is `deterministic_replay`. Because allowed requests reuse the
same retained candidates, differences are attributable to guardrail and deterministic
evaluation treatment rather than a newly sampled model response.

## Real guardrailed run

Only after explicit authorization for credentials and provider spend, run:

```bash
python -m llm_eval_guardrails run-openai-guardrailed \
  benchmarks/northstar_bank_v1.jsonl \
  evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905 \
  /path/to/new-guardrailed-bundle \
  --run-id RUN_ID
```

The command reads the exact model ID, maximum output tokens, prompt version, and context
format from the selected baseline. It rejects a dataset mismatch or an unavailable local
prompt/format version before provider construction. It never substitutes another model.
The SDK reads `OPENAI_API_KEY` through its standard environment path; credentials must not
appear in arguments or artefacts. The command uses the same no-retry, `store=False`,
sequential provider path documented for Batch A and makes at most one application-level
provider invocation for each input-allowed case.

The emitted comparison mode is `fresh_provider_execution`. Its report distinguishes the
directly attributable input-block invocation avoidance from PASS/WARN output transitions
and deterministic metric deltas. Those other differences are observational and potentially
confounded by provider or model nondeterminism, so the report does not title or describe
them as clean causal guardrail impact.

The new directory contains:

- `raw-run.json` and `evaluated-run.json`;
- `summary.json` and `report.md`;
- `guardrail-decisions.json`; and
- `comparison.json` and `comparison.md`.

Comparison evidence references are explicit `{base, path}` objects. Guardrailed artefacts
are relative to the comparison bundle. A retained in-repository baseline is relative to the
repository root; a sibling baseline may be relative to the comparison bundle. Resolution
starts at the declared base, never the current working directory. The command rejects a
baseline outside both stable locations rather than retaining a machine-specific absolute
path or a misleading relative path.

Generated bundles remain untracked until every raw output, decision, evaluation,
comparison metric, configuration difference, and confidentiality concern has been reviewed.
Real evidence must never be described as measured until that authorized run and inspection
have completed.
