# Project Vision

## Purpose

Build a defensible, explainable system for evaluating LLM applications and applying configurable guardrail policies. The project should demonstrate sound evaluation engineering and governance judgement rather than imitate a production platform.

## Problem

LLM applications can fail in ways that ordinary unit tests do not capture. Outputs may be plausible but unsupported, ignore instructions, leak sensitive context, follow malicious embedded instructions, refuse safe requests, or comply with unsafe ones. Teams need repeatable evidence about these behaviours before they can make sensible release or enforcement decisions.

## Intended users

- an AI/ML engineer comparing application or model behaviour;
- a developer adding regression tests for an LLM workflow;
- a risk or governance reviewer examining evidence and thresholds; and
- the project owner, explaining the design and trade-offs in technical interviews.

## Target system

The mature system should support:

1. versioned, structured evaluation cases and datasets;
2. a provider-agnostic interface for systems under test;
3. reproducible evaluation runs with captured inputs, outputs, configuration, and timing;
4. deterministic, reference-based, structured-assertion, and model-based evaluators;
5. adversarial suites for injection, leakage, unsafe requests, and policy bypass;
6. aggregation that preserves per-case evidence and uncertainty;
7. explicit risk policies that can produce allow, block, redact, review, or error decisions; and
8. human-readable and machine-readable reports.

## Evaluation philosophy

Evaluation is measurement, not proof. A score is useful only when its definition, evidence, limitations, and aggregation are visible.

- Use deterministic checks when the property is objectively testable.
- Use references or structured assertions when acceptable behaviour can be specified.
- Use model-based evaluation only where semantic judgement is necessary.
- Preserve component results rather than hiding them behind one composite number.
- Calibrate judges against human-labelled examples and examine disagreement.
- Report uncertainty, missing evidence, and evaluator errors distinctly from failures.
- Test both unsafe compliance and inappropriate refusal.

## Evaluation versus guardrails

Evaluation components observe and score behaviour. Guardrails enforce constraints before or after model execution. They can share detectors and policy definitions, but they must not share ambiguous outcomes or silently mutate evaluation evidence.

## Principles

- **Truthful:** claims match implemented and measured behaviour.
- **Reproducible:** datasets, configuration, prompts, model identifiers, and outputs are traceable.
- **Provider-agnostic:** core contracts do not depend on one vendor SDK.
- **Risk-oriented:** test selection reflects failure impact, not just happy-path quality.
- **Explainable:** every aggregate result can be traced to case-level evidence.
- **Incremental:** each milestone is small enough to test and understand.
- **Proportionate:** avoid services and abstractions until a demonstrated need exists.

## In scope

- offline evaluation of text-based LLM applications;
- deterministic and semantic scoring;
- adversarial and regression datasets;
- configurable thresholds and risk policies;
- local experiment artefacts and reports;
- tests, calibration, and methodology documentation.

## Out of scope for the initial roadmap

- claiming formal security guarantees;
- a hosted multi-tenant platform;
- real-time production monitoring;
- a general-purpose prompt-management product;
- automatic model fine-tuning;
- multimodal evaluation;
- compliance certification or legal conclusions.

These may be reconsidered only when the core evaluation system is sound and a concrete use case justifies them.

## Definition of success

The project succeeds when a reviewer can inspect a versioned suite, reproduce a run, trace metrics to evidence, understand evaluator limitations, and explain why a policy decision was produced. The project owner should be able to defend the architecture, methodology, trade-offs, tests, and remaining risks.

