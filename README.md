# Enterprise LLM Evaluation & Guardrails

A portfolio and learning project for measuring the behaviour of LLM applications and, later, enforcing explicit risk policies around them. The project is designed for settings where reliability, traceability, privacy, safety, and groundedness matter.

The reference system is a fictional bank's LLM-powered customer-support assistant.
This gives the evaluation work a realistic, risk-sensitive setting without implying
access to real customer data, bank systems, or confidential policies. The framework's
core contracts remain provider-agnostic.

> **Current status:** Milestones M0, M1, and M2 and capability Batches A and B are complete.
> The repository retains both the measured baseline and the measured fresh-provider
> guardrail comparison, with runtime decisions kept separate from deterministic evaluation.
> Semantic evaluation is not implemented.

## Why this project exists

LLM demonstrations often show that a model can answer a prompt. They do not show how reliably it behaves across normal, edge, and adversarial conditions. This project will provide a reproducible way to:

- define structured evaluation cases;
- run an application or model against versioned datasets;
- score outputs with deterministic, reference-based, and model-based evaluators;
- test prompt injection, data leakage, unsafe behaviour, and refusal quality;
- aggregate evidence into transparent metrics and policy decisions; and
- compare experiments without presenting an LLM judge as ground truth.

Evaluation and enforcement are deliberately separate: evaluators produce evidence about behaviour; guardrails use explicit policies to allow, block, redact, or escalate a request or response.

## Target architecture

```text
Versioned cases -> Evaluation runner -> System under test -> Raw run records
                                           |
Raw run records -> Evaluators --------------+
       |               |
       |               +-> deterministic / reference / model-based scores
       v
Aggregation and reports -> risk policy decisions (separate enforcement layer)
```

Runtime guardrails wrap only the system request/candidate-response boundary. Their decisions
remain in a dedicated artefact and never become deterministic evaluation outcomes.

The architecture is intentionally local-first and provider-agnostic. Early milestones favour simple Python interfaces and files over services, databases, or orchestration frameworks.

## Evaluation dimensions

The planned evaluation contract covers:

- reliability and instruction following;
- relevance and task completion;
- groundedness and unsupported claims;
- safety and refusal behaviour;
- privacy and sensitive-data leakage;
- prompt-injection and policy-bypass resistance.

See [the evaluation specification](docs/EVALUATION_SPEC.md) for the initial measurement model and limitations.

## Repository map

```text
src/llm_eval_guardrails/  Python package
tests/                    Automated tests
tests/fixtures/           Valid and invalid loader fixtures
examples/                 Illustrative input data (not evaluation evidence)
benchmarks/               Versioned fictional evaluation benchmarks
evidence/                 Reviewed, deliberately retained real-run evidence only
docs/                     Methodology and technical specifications
PROJECT_VISION.md         Stable purpose, scope, and principles
ROADMAP.md                Planned milestones
PROJECT_STATE.md          Honest snapshot of implemented work
DECISIONS.md              Architecture and methodology decision log
```

## Development setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

The dependency-free core and offline evaluation workflow require no provider credentials.
Install `.[dev,openai]` only when preparing an authorized OpenAI run.

## What is implemented now

- a Python package scaffold;
- a documented evaluation contract and outcome taxonomy;
- a typed, explicitly versioned evaluation-case representation;
- a strict UTF-8 JSONL dataset loader with source-aware validation errors;
- duplicate case-ID detection and deterministic input ordering;
- a synchronous, provider-agnostic system-under-test protocol with typed requests and
  responses;
- a deterministic echo test double for exercising invocation plumbing;
- a sequential runner with per-case exception isolation and monotonic durations;
- validated versioned JSON run artefacts with ordered case snapshots and SHA-256
  fingerprints;
- literal execution of schema-v1 `exact_match`, `contains`, and `not_contains` assertions;
- separate validated evaluation artefacts with explicit pass, fail, error, and
  not-applicable semantics and strict raw-evidence joins;
- reconciled aggregation with explicit denominators, coverage, per-risk-category results,
  case traces, and shared JSON/Markdown rendering;
- an isolated optional OpenAI Responses API adapter with explicit model and prompt
  provenance;
- a versioned 36-case fictional Northstar Bank benchmark with adversarial and benign
  paired controls;
- offline re-evaluation and atomic end-to-end output-bundle commands;
- narrow versioned input BLOCK, input WARN, and response BLOCK detectors with explicit
  precedence and versioned replacement responses;
- one separate, canonically joined guardrail decision per case;
- matched baseline-to-guardrailed JSON/Markdown comparison with false-refusal,
  adversarial-decision, detector-trigger, invocation-avoidance, transition, and case-trace
  evidence;
- atomic deterministic-replay and provider-backed guardrailed workflows;
- a local synthetic echo-run command requiring no provider credentials;
- representative fixtures and an illustrative example dataset;
- a milestone roadmap with verification criteria;
- test, lint, and continuous-integration configuration; and
- an explicit record of architectural decisions.

Sections that describe the case schema, system interface, runner, raw/evaluated artefacts,
guardrails, and reporting document implemented capability. Reviewed provider-backed
evidence is retained separately for the four-file Batch A baseline and seven-file Batch B
guardrail comparison.

## Measured Batch B guardrail comparison

Batch B keeps benchmark specification, externally observed raw output, deterministic
evaluation, and guardrail/comparison decisions distinct. Its retained fresh-provider run
used the same 36-case benchmark and fingerprint
`6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698`.

Nine deterministic input blocks directly avoided provider invocation, leaving 27 provider
requests; all 27 completed successfully and their candidates were released. Decisions were
24 PASS, 3 WARN, and 9 BLOCK, with no response-detector triggers or response replacements.
Of the 27 released outputs, 21 differed textually from the retained baseline.

The baseline passed 36/38 literal assertions; the guardrailed run passed 35/38. The only
evaluation transition was `unsupported-mortgage-eligibility`, pass → fail, because its
input-block response does not contain the benchmark's insufficient-information phrase.
Input-block avoidance is directly attributable to the guardrail. Differences involving
freshly generated PASS/WARN responses remain observational and potentially confounded by
provider/model nondeterminism. BLOCK totals are policy-decision observations, not accuracy
or proof of general safety effectiveness.

See the [retained Batch B evidence bundle](evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/)
and its [observational comparison report](evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/comparison.md).
See the [Batch B workflow](docs/GUARDRAIL_WORKFLOW.md), [policy](docs/GUARDRAIL_POLICY.md),
[decision artefact](docs/GUARDRAIL_ARTIFACT_SPEC.md), and
[comparison artefact](docs/GUARDRAIL_COMPARISON_SPEC.md).

## Measured Batch A baseline

The 36-case Northstar Bank benchmark was run once against the exact model snapshot
`gpt-5.4-mini-2026-03-17`. All 36 executions completed successfully. Deterministic
evaluation passed 36 of 38 configured literal assertions (94.74%); 31 of 36 cases had at
least one deterministic assertion, and five remain semantically unassessed. The two failed
assertions were literal wording mismatches, not execution errors.

See the [retained Markdown report](evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/report.md)
for category results and case-level traceability into raw and evaluated evidence. Execution
success does not mean evaluation success, and these narrow configured checks do not
establish semantic correctness, safety, privacy, prompt-injection robustness, security, or
production readiness. Provider usage was not retained, so the actual token cost cannot be
reconstructed from the evidence.

## Evaluation-case schema v1

Each applicable JSONL line must contain one JSON object. The object must include:

- `schema_version`: exactly the string `"1"`;
- `id`: a non-empty case identifier, unique within the file; and
- `input`: the non-empty text supplied to the system under test.

These fields are optional:

- `context`: an array of non-empty context strings;
- `references`: an array of non-empty reference strings;
- `tags`: an array of unique, non-empty categorisation strings;
- `risk_category`: one of `reliability`, `relevance`, `groundedness`,
  `instruction_following`, `safety`, `privacy`, `injection_resistance`, or
  `refusal_behavior`;
- `expected_behavior`: a non-empty human-readable description;
- `assertions`: an array of named assertions with unique `criterion` values, a `type`
  of `exact_match`, `contains`, or `not_contains`, and a non-empty string `value`; and
- `metadata`: an object containing JSON-compatible values. Numeric values must be
  finite; `NaN`, positive infinity, and negative infinity are rejected recursively.
  Metadata is the only open-ended extension area in v1.

Unknown case and assertion fields are rejected. Missing optional arrays behave as
empty arrays; missing scalar options behave as absent values. An optional field that is
present must contain its documented type, so JSON `null` is not accepted for optional
strings or arrays. Validation preserves the original strings and does not trim or
coerce them. The exported `EvaluationCase` and `EvaluationAssertion` constructors also
enforce their typed domain contracts.

`EvaluationCase` is shallowly frozen: its attributes cannot be rebound, and its
sequence fields are tuples. Metadata is validated and recursively copied during
construction so it does not alias caller-owned input, but the case-owned metadata
dictionary and nested dictionaries or lists remain mutable. `to_mapping()` validates
the metadata's current state and returns another recursive copy, so invalid mutations
are detected at serialization time and mutation of serialized output does not alter
the case. Every mapping successfully returned by `to_mapping()` contains only
standards-compliant JSON values.

Example input:

```json
{"schema_version":"1","id":"refund-policy","input":"Can I get a refund after 14 days?","context":["Refunds are available within 30 days."],"tags":["support"],"risk_category":"groundedness","expected_behavior":"Answer using only the supplied policy.","assertions":[{"criterion":"mentions-window","type":"contains","value":"30 days"}]}
```

This is an authoring example, not a benchmark result. A larger valid example is in
[`examples/evaluation_cases.jsonl`](examples/evaluation_cases.jsonl).

Load a dataset with:

```python
from llm_eval_guardrails import load_dataset

cases = load_dataset("examples/evaluation_cases.jsonl")
```

The loader reads UTF-8, preserves record order, and validates the complete file before
returning. Blank and whitespace-only lines are ignored and do not count as records;
physical line numbers are retained in errors. Empty and blank-only files, malformed
JSON, duplicate JSON object keys, non-object records, unsupported or missing versions,
non-standard numeric constants, invalid fields, unknown fields, and duplicate IDs raise
`DatasetError` with file, line, record, known case ID, and field context where
applicable. The original parsing or validation error is retained as the cause.

## System-under-test interface

`SystemUnderTest` is a synchronous structural protocol: adapters implement
`invoke(SystemRequest) -> SystemResponse` without inheriting from a project base class.
`SystemRequest` contains only the input text and ordered supplied context. Case identity,
references, assertions, expected behaviour, risk labels, tags, and metadata remain with
the evaluation layer and are not system inputs. Requests follow the case schema's
non-empty string conventions and preserve accepted strings and context order without
trimming or coercion. `SystemResponse` contains the raw output text; an empty output
string is valid and remains observable for downstream evaluation, while a non-string output
is rejected.

Implementations may raise ordinary exceptions. The interface does not turn exceptions
into successful output or provide a fallback. The baseline runner isolates and records
ordinary failures per case.

This example invokes the deterministic echo double using a loaded case:

```python
from llm_eval_guardrails import EchoSystemUnderTest, SystemRequest, load_dataset

case = load_dataset("examples/evaluation_cases.jsonl")[0]
request = SystemRequest(input=case.input, context=case.context)
response = EchoSystemUnderTest().invoke(request)

print(response.output)
```

The echo double returns the input verbatim and deliberately ignores context. Its output
is only a plumbing demonstration: it is not evaluation evidence and does not simulate
model intelligence, banking correctness, or safety.

## Sequential baseline runner

`run_dataset()` validates the complete dataset before invoking the system. It then
constructs one `SystemRequest` per case, in source order, using only `case.input` and
`case.context`. The complete validated case remains separately available in dataset
provenance. Each invocation produces exactly one `CaseExecutionResult` in a normally
completed run.

Execution status is deliberately not an evaluation outcome. `success` means the system
returned a valid `SystemResponse`, including a valid empty output string. Ordinary
exceptions and invalid response objects become `error` results with `output=None`, and
execution continues. Interrupts propagate, as do dataset and artefact-writing failures.

Python API:

```python
from llm_eval_guardrails import (
    EchoSystemUnderTest,
    run_dataset,
    write_run_artifact,
)

artifact = run_dataset(
    "examples/evaluation_cases.jsonl",
    EchoSystemUnderTest(),
    system_id="echo",
    system_configuration={
        "behavior": "input_verbatim",
        "context_usage": "ignored",
    },
)
write_run_artifact(artifact, "/tmp/synthetic-echo-run.json")
```

The configuration argument is an explicit allowlist of effective, non-secret settings.
The runner never introspects the adapter, which prevents credentials stored on it from
being serialized. There is no automatic secret detection or redaction; callers are
responsible for keeping credentials and other secrets out of the allowlist.

Run the same synthetic plumbing demonstration locally with:

```bash
python -m llm_eval_guardrails run-echo \
  examples/evaluation_cases.jsonl \
  /tmp/synthetic-echo-run.json \
  --run-id synthetic-echo-demo
```

The output path must not already exist. This command records synthetic echo behavior;
it is not a model evaluation or evidence of quality, banking correctness, or safety.
See [the run artefact specification](docs/RUN_ARTIFACT_SPEC.md) for the versioned JSON
contract, fingerprint algorithm, timing units, error semantics, and limitations.

## Deterministic evaluation and reporting

`evaluate_run()` applies each configured assertion directly to successful raw output.
Comparisons are case-sensitive and literal, with no trimming, Unicode normalization,
rewriting, or semantic interpretation. Execution errors remain execution errors and
produce explicit evaluation-error evidence; successful cases without assertions are
`not_applicable`.

The separate evaluation artefact is joined to raw evidence by run ID, dataset fingerprint,
ordered case IDs, and execution statuses, then every stored outcome and evidence field is
checked against a canonical recomputation from the raw run. Aggregation exposes assertion
pass rate, assertion evaluation coverage, deterministic case coverage, errors, and
non-applicable cases rather than allowing excluded evidence to inflate a result. JSON and
Markdown reports come from the same aggregate and support exact persisted-output
comparison.

Run an offline evaluation bundle with:

```bash
python -m llm_eval_guardrails evaluate \
  /path/to/raw-run.json \
  /path/to/new-evaluation-bundle
```

The output directory must not exist. See the
[evaluation artefact specification](docs/EVALUATION_ARTIFACT_SPEC.md) for exact semantics
and denominators.

## Fictional-bank OpenAI baseline

The optional adapter uses the official OpenAI Python SDK and Responses API. Its model is a
required CLI option; credentials are read by the SDK from `OPENAI_API_KEY` and are never a
CLI argument or provenance field. Only request input and ordered context are formatted for
the provider, alongside the versioned fixed system instructions. The real client disables
SDK retries, every request sets `store=False`, and only top-level status `completed` is
accepted. The non-secret provenance includes the installed SDK version.

After explicit model selection and paid-use authorization, the complete 36-request workflow
is:

```bash
python -m llm_eval_guardrails run-openai \
  benchmarks/northstar_bank_v1.jsonl \
  /path/to/new-openai-baseline-bundle \
  --model MODEL_ID \
  --max-output-tokens 800 \
  --run-id RUN_ID
```

The four-file bundle is published atomically only after raw evidence, evaluated evidence,
JSON summary, and Markdown report all succeed. The versioned assistant prompt is part of
the baseline system, not a runtime guardrail or security guarantee. Benchmark composition,
credential handling, reproduction, and evidence-retention review are documented in the
[baseline workflow](docs/BASELINE_WORKFLOW.md).

The matched Batch B provider command deliberately derives the exact model snapshot and
request configuration from that retained baseline rather than accepting a substitute:

```bash
python -m llm_eval_guardrails run-openai-guardrailed \
  benchmarks/northstar_bank_v1.jsonl \
  evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905 \
  /path/to/new-guardrailed-bundle \
  --run-id RUN_ID
```

Do not run it until credentials and provider spend have been explicitly authorized.

The command derives `fresh_provider_execution` from the workflow and emits portable,
explicitly based evidence references. Fresh-provider comparison titles and attribution
language do not imply that all observed deltas are caused by guardrails.

The baseline command makes 36 application-level calls if every case is attempted; the
guardrailed command makes one call only for each input-allowed case. Disabling SDK retries
prevents automatic retry HTTP attempts by the SDK; no application retries or fallbacks
exist. `store=False` minimizes Responses application-state retention, but does not remove
default provider abuse-monitoring retention or confer account-level Zero Data Retention.
Only fictional and synthetic benchmark data is sent.

## Limitations

- Deterministic string checks have narrow literal coverage and cannot establish semantic
  correctness, safety, groundedness, privacy, or injection resistance.
- Guardrails are narrow regex/phrase/digit-shape rules, not semantic understanding, a broad
  PII catalogue, redaction, or a security guarantee. No model-based judge, semantic score,
  regex assertion, dashboard, or second provider is implemented.
- The runner is sequential and has no application or SDK retries, resume support, or
  concurrency.
- Run provenance supports case reconstruction and change detection but does not guarantee
  repeatable responses from nondeterministic systems.
- A fingerprint validates the case snapshot in its current stored state. Case metadata
  remains mutable and fingerprints are calculated on demand, so it is not an immutable
  identity of the snapshot at execution time.
- Complete case snapshots, raw outputs, and exception messages may contain sensitive
  information. The runner performs no automatic redaction.
- Schema v1 has no migration utility; future loaders can dispatch on the required
  `schema_version` without changing v1 data.
- Each retained run is one finite observation; together they do not support general
  robustness, accuracy, safety, privacy, or security claims.
- Provider token usage was not retained, so actual run cost cannot be reconstructed from
  the evidence.
- The measurement design will need calibration against labelled examples once model-based judging is introduced.

## Working principles

- Never fabricate results; label illustrative output clearly.
- Preserve raw evidence and configuration needed to reproduce a run.
- Prefer multiple complementary evaluators over a single opaque score.
- Treat model-based judging as noisy measurement.
- Make thresholds and policy choices explicit.
- Deliver bounded vertical capability batches, using independently testable increments
  inside each batch.
