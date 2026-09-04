# Enterprise LLM Evaluation & Guardrails

A portfolio and learning project for measuring the behaviour of LLM applications and, later, enforcing explicit risk policies around them. The project is designed for settings where reliability, traceability, privacy, safety, and groundedness matter.

The reference system is a fictional bank's LLM-powered customer-support assistant.
This gives the evaluation work a realistic, risk-sensitive setting without implying
access to real customer data, bank systems, or confidential policies. The framework's
core contracts remain provider-agnostic.

> **Current status:** Milestones M0 and M1 are complete. The repository provides a
> versioned evaluation-case schema and strict local JSONL loader. It does not yet run
> model evaluations, score outputs, or enforce guardrails.

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

No model provider credentials are required for the implemented milestones.

## What is implemented now

- a Python package scaffold;
- a documented evaluation contract and outcome taxonomy;
- a typed, explicitly versioned evaluation-case representation;
- a strict UTF-8 JSONL dataset loader with source-aware validation errors;
- duplicate case-ID detection and deterministic input ordering;
- representative fixtures and an illustrative example dataset;
- a milestone roadmap with verification criteria;
- test, lint, and continuous-integration configuration; and
- an explicit record of architectural decisions.

Everything else in this README is a target, not a claim of completed capability.

## Evaluation-case schema v1

Each applicable JSONL line must contain one JSON object. The object must include:

- `schema_version`: exactly the string `"1"`;
- `id`: a non-empty case identifier, unique within the file; and
- `input`: the non-empty text supplied to the future system under test.

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

## Limitations

- No model provider or application adapter exists yet.
- No evaluation, scoring, guardrail, reporting, or red-team runtime exists yet.
- Assertion definitions are validated and stored but are not executed yet.
- Schema v1 has no migration utility; future loaders can dispatch on the required
  `schema_version` without changing v1 data.
- No empirical robustness, accuracy, or security claims can be made.
- The measurement design will need calibration against labelled examples once model-based judging is introduced.

## Working principles

- Never fabricate results; label illustrative output clearly.
- Preserve raw evidence and configuration needed to reproduce a run.
- Prefer multiple complementary evaluators over a single opaque score.
- Treat model-based judging as noisy measurement.
- Make thresholds and policy choices explicit.
- Build one independently testable milestone at a time.
