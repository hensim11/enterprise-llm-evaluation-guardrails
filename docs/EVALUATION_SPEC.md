# Initial Evaluation Specification

This document defines the initial measurement contract. Case specification, raw execution,
deterministic string evaluation, runtime guardrails, and the semantic-evaluation
implementation are present. Human semantic calibration and real judge measurements remain
pending; runtime risk-threshold policy remains planned.

## Unit of evaluation

An **evaluation case** is the smallest versioned test specification. It will identify an input, relevant context, risk metadata, and zero or more expectations. A **run** applies a fixed system and configuration to a versioned dataset and records one result per case.

The architecture preserves three layers, all now represented by separate versioned
artefacts for deterministic evaluation:

1. **Case specification:** what behaviour is being tested.
2. **Raw execution:** what the system produced under a recorded configuration.
3. **Evaluation result:** how a named evaluator interpreted that output, including evidence.

This separation allows the same raw output to be re-evaluated without another model call and prevents a score from replacing the underlying evidence.

## Initial dimensions

| Dimension | Question | Suitable evidence |
| --- | --- | --- |
| Reliability | Does the system behave consistently and complete the requested task? | execution status, repeated trials, structured assertions |
| Relevance | Does the response address the request without material distraction? | references, rubric-based semantic judgement |
| Groundedness | Are material claims supported by the supplied context or cited evidence? | claim/evidence matching, attribution checks, judge rubric |
| Instruction following | Did the response obey explicit format and behavioural constraints? | schema checks, exact assertions, rubric-based judgement |
| Safety | Does the response avoid disallowed assistance while remaining useful where possible? | policy-labelled cases, refusal/compliance classification |
| Privacy | Does the response expose secrets or sensitive data it should not reveal? | canary matching, pattern checks, semantic leakage assessment |
| Injection resistance | Does the system preserve trusted instructions when untrusted content conflicts? | adversarial cases plus benign controls |
| Refusal behaviour | Does it refuse harmful requests and avoid refusing acceptable ones? | paired unsafe/safe cases, refusal-quality rubric |

Dimensions must not be collapsed into a universal score without an explicit, documented use case. A severe privacy failure is not cancelled out by high relevance.

## Outcome taxonomy

Every evaluator should produce one of these states before optional numeric aggregation:

- **pass:** the stated criterion was satisfied;
- **fail:** the criterion was evaluated and not satisfied;
- **error:** evaluation could not complete or its output was invalid;
- **not_applicable:** the criterion does not apply to this case.

`error` and `not_applicable` must never be silently counted as `pass`. Evaluators should attach a criterion identifier, method/version, human-readable explanation, and structured evidence where appropriate.

## Evaluation methods

### Deterministic checks

The implemented v1 checks are exact match, literal substring inclusion, and literal
substring exclusion. They use case-sensitive raw strings without normalization. Regular
expressions, JSON/schema checks, and other deterministic methods remain future work. These
checks are reproducible and easy to debug but cannot reliably measure broad semantic
quality. See [the artefact specification](EVALUATION_ARTIFACT_SPEC.md).

### Reference-based checks

Use where a trusted answer, fact set, or allowed-answer set exists. References should not imply that surface-form similarity always equals correctness.

### Structured assertions

Use executable expectations attached to a case, such as required citations or forbidden disclosure categories. Assertion types need explicit versions or stable semantics.

### Model-based evaluation

Use when semantic interpretation is genuinely needed. A judge result must identify its model/configuration and rubric version, validate structured output, and retain enough evidence for review. It remains an estimate affected by bias, variance, prompt wording, model changes, and possible shared failure modes with the system being judged.

The implemented version-1 semantic rubric uses binary completed outcomes against authored
expected behaviour, with explicit error/N/A states, exact response excerpts, confidence,
and failure modes in a separate strictly joined artefact. See
[the semantic rubric](SEMANTIC_RUBRIC.md),
[artefact specification](SEMANTIC_ARTIFACT_SPEC.md), and
[calibration workflow](CALIBRATION_WORKFLOW.md). No real judge measurement is retained yet.

### Adversarial evaluation

Use threat-informed cases and benign controls. Passing a finite suite demonstrates observed behaviour only; it does not establish that a system is secure against prompt injection or leakage.

## Aggregation principles

- Retain case-level and evaluator-level results.
- Report denominators and counts of errors/not-applicable outcomes.
- Aggregate by relevant tags and risk categories, not only globally.
- Keep critical failure counts visible alongside averages.
- Version threshold and weighting policies.
- Never compare runs whose material configuration differences are unknown.

## Reproducibility record

A mature run artefact should record, where available:

- dataset identifier, content/version, and case IDs;
- system adapter and configuration;
- model/provider identifiers and generation settings;
- evaluator names, versions, rubrics, and thresholds;
- timestamps, durations, retry/error information, and random seeds;
- code revision and run-format version;
- raw outputs and evaluator evidence, subject to privacy policy.

Credentials and sensitive source data must not be stored in run artefacts.

## Calibration and review

Before relying on a model-based metric, compare it with a small human-labelled set, inspect disagreements, and repeat a sample to estimate variance. Calibration does not turn subjective judgement into truth; it reveals where the measurement is useful or weak.

## Open questions for later milestones

- Which risk taxonomy provides enough structure without implying regulatory coverage?
- How should sensitive evidence be redacted while retaining reproducibility?
- Which agreement and variance measures are proportionate for the first judge calibration?
- When is a composite score useful, and which critical failures must override it?
