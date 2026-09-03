# Enterprise LLM Evaluation & Guardrails

A portfolio and learning project for measuring the behaviour of LLM applications and, later, enforcing explicit risk policies around them. The project is designed for settings where reliability, traceability, privacy, safety, and groundedness matter.

> **Current status:** Milestone M0 is complete. This repository defines the project contract, evaluation philosophy, target architecture, and development standards. It does not yet run model evaluations or enforce guardrails.

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
src/llm_eval_guardrails/  Python package (foundation only)
tests/                    Automated tests
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

No model provider credentials are required at M0.

## What is implemented now

- a Python package scaffold;
- a documented evaluation contract and outcome taxonomy;
- a milestone roadmap with verification criteria;
- baseline test, lint, and continuous-integration configuration; and
- an explicit record of architectural decisions.

Everything else in this README is a target, not a claim of completed capability. The next objective is M1: a typed evaluation-case schema, dataset loader, validation errors, example fixtures, and tests.

## Limitations

- No dataset schema or loader exists yet.
- No model provider or application adapter exists yet.
- No evaluation, scoring, guardrail, reporting, or red-team runtime exists yet.
- No empirical robustness, accuracy, or security claims can be made.
- The measurement design will need calibration against labelled examples once model-based judging is introduced.

## Working principles

- Never fabricate results; label illustrative output clearly.
- Preserve raw evidence and configuration needed to reproduce a run.
- Prefer multiple complementary evaluators over a single opaque score.
- Treat model-based judging as noisy measurement.
- Make thresholds and policy choices explicit.
- Build one independently testable milestone at a time.

