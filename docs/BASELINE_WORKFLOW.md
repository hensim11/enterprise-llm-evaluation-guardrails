# First Baseline Workflow

## Data flow

```text
northstar_bank_v1.jsonl
  -> provider-neutral sequential runner -> raw-run.json
  -> deterministic string evaluator     -> evaluated-run.json
  -> one reconciled aggregate            -> summary.json + report.md
```

The system request contains only customer input and ordered context. The raw artefact
retains the full case snapshot for audit, while evaluated evidence stays in its own
versioned artefact. Reports require an exact run/fingerprint/case-order join.

Bundle commands write into a temporary sibling directory and publish the final output
directory with one rename only after every file succeeds. The requested output directory
must not exist and its parent must already exist.

## Fictional-bank benchmark v1

[`benchmarks/northstar_bank_v1.jsonl`](../benchmarks/northstar_bank_v1.jsonl) contains 36
synthetic cases, 38 literal assertions, and five cases intentionally left without a
deterministic assertion. All products, policies, identifiers, and canaries are fictional.

| Scenario family | Cases |
| --- | ---: |
| Ordinary support | 6 |
| Grounded policy | 6 |
| Unsupported-claim / hallucination traps | 5 |
| Financial/refusal boundaries (including benign control) | 5 |
| Privacy (including benign control) | 5 |
| Prompt injection / extraction | 5 |
| Additional benign controls | 4 |
| **Total** | **36** |

The cases span eight risk categories. Thirteen are explicitly tagged adversarial, six are
tagged benign controls, and paired-control metadata links important adversarial and benign
conditions. Assertions comprise 28 `contains`, nine `not_contains`, and one `exact_match`.
Human-readable expected behaviour is broader than these checks; no assertion is presented
as semantic proof.

## Offline re-evaluation

Evaluate an existing raw artefact without provider access:

```bash
python -m llm_eval_guardrails evaluate \
  /path/to/raw-run.json \
  /path/to/new-evaluation-bundle
```

The new directory contains `evaluated-run.json`, `summary.json`, and `report.md`. The raw
artefact remains at the source path and is referenced by both reports. Loading evaluated
evidence with its raw run recomputes every deterministic result and rejects any persisted
outcome, error, or explanation that differs. Reviewed summaries are regenerated from that
canonical evidence and compared exactly in both JSON and Markdown forms.

## OpenAI baseline

Install the optional provider dependency:

```bash
python -m pip install -e ".[dev,openai]"
```

Set `OPENAI_API_KEY` through the standard SDK environment mechanism. Never put it in a CLI
argument, dataset, prompt, configuration mapping, output file, or commit. The adapter uses
the official Python SDK's Responses API. The model is mandatory and has no implicit
default. The optional dependency is constrained to `openai>=1.66.0,<3.0`. Version 1.66.0
was inspected directly and contains the used Responses `create`, `store`, response-status,
ordered output-message structure, distinct output-text/refusal blocks, and client
`max_retries` surfaces. The exact installed SDK version is stored in the run's non-secret
system configuration; this fits the existing open configuration object and does not change
raw artefact schema v1.

After explicitly approving the model and paid use, run:

```bash
python -m llm_eval_guardrails run-openai \
  benchmarks/northstar_bank_v1.jsonl \
  /path/to/new-openai-baseline-bundle \
  --model MODEL_ID \
  --max-output-tokens 800 \
  --run-id RUN_ID
```

This makes 36 sequential application-level `responses.create` calls if all cases are
attempted. There are no application-level retries, and the SDK client is constructed with
`max_retries=0`, so the SDK does not add retry HTTP attempts. This does not make claims
about lower-level transport, proxy, or network behaviour outside the SDK. There is no
concurrency or fallback model. Ordinary provider exceptions follow the existing per-case
raw-error path. Only a response whose top-level status is exactly `completed` can become a
successful raw execution; incomplete, failed, cancelled, in-progress, missing, and unknown
statuses are errors even if partial output is present. The completed directory contains
`raw-run.json`, `evaluated-run.json`, `summary.json`, and `report.md`.

The versioned `northstar-bank-assistant-v1` instructions and `ordered-context-v1` formatter
are baseline-system configuration. They ask the model to stay grounded, protect sensitive
tokens, and ignore embedded instructions, but are not an independent runtime guardrail or
security guarantee. Every request explicitly supplies `store=False` to avoid retaining the
response as Responses API application state for later retrieval. This does not eliminate
OpenAI abuse-monitoring logs: under default controls, prompts and responses may be retained
there for up to 30 days. It also does not establish that the account has Modified Abuse
Monitoring or Zero Data Retention. This benchmark sends only fictional policies,
identifiers, and synthetic canaries; real customer data is not involved or permitted. See
OpenAI's [data controls documentation](https://developers.openai.com/api/docs/guides/your-data)
for current endpoint and account-level retention details.

Provider provenance stores only provider, API, installed SDK version, explicit model,
prompt version, context-format version, and maximum output tokens.

## Retained Batch A baseline

One authorized baseline has been retained at
[`evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/`](../evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/).
It has run ID `northstar-v1-gpt-5.4-mini-2026-03-17-20260905`, model snapshot
`gpt-5.4-mini-2026-03-17`, and dataset fingerprint
`6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698`.
The run used SDK 1.66.0, `max_retries=0`, and `store=False`; all 36 executions completed.

Disabling Responses application-state storage does not disable provider abuse-monitoring
retention or establish Zero Data Retention. Provider usage metadata is not part of raw
artefact schema v1, so actual token usage and cost cannot be reconstructed from the retained
files. Any future paid run requires fresh authorization and a fresh output directory; it
must not overwrite or merge with this evidence.

## Retaining real evidence

Generated output stays untracked by default. Before publishing any real run:

1. inspect every raw and evaluated case record;
2. independently verify aggregate counts against those exact records;
3. check that no credential, private input, or inappropriate provider metadata appears;
4. copy only the reviewed four-file package to
   `evidence/baselines/<run-id>/`, the deliberately tracked location described in
   [`evidence/README.md`](../evidence/README.md); and
5. derive every published metric from those retained files without hand-editing.

The accepted Batch A package followed this review process. Offline echo or fake-client
artefacts remain plumbing and test evidence only, never measured model results.
