# Roadmap

Status values: **complete**, **in progress**, **not started**. A milestone is complete only when its stated verification is satisfied.

## M0 — Foundation and evaluation specification — complete

Establish the repository contract before implementing evaluation behaviour.

Delivered:

- project vision, scope, and principles;
- initial evaluation specification and outcome taxonomy;
- target architecture and separation of evaluation from enforcement;
- Python package, test, lint, and CI scaffold;
- state document and decision log.

Verification:

- package imports and exposes a version;
- repository contract tests pass;
- lint configuration is valid;
- planned features are labelled as planned.

## M1 — Evaluation-case schema and dataset loading — complete

Create a typed, versioned case format and reliable local loader.

Delivered in schema version `"1"` with strict UTF-8 JSONL loading, validated typed
cases, source-aware errors, duplicate-ID detection, defensive metadata copying,
fixtures, tests, and authoring guidance.

Expected completion criteria:

- schema covers stable IDs, inputs, optional references, tags, risk category, and structured expectations;
- datasets declare a schema version;
- duplicate IDs, malformed values, unknown schema versions, and invalid expectations fail with actionable errors;
- representative valid and invalid fixtures exist;
- unit tests cover parsing and validation boundaries;
- documentation includes a minimal authoring example.

## M2 — Provider-agnostic system interface and baseline runner — complete

Run a dataset against a deterministic test double and record reproducible case-level results.

Expected completion criteria:

- the system-under-test interface has no vendor SDK dependency;
- runner records case ID, output, status, duration, configuration, and error details;
- one case failure does not corrupt the rest of a run;
- deterministic test doubles support repeatable tests;
- run artefacts use a documented versioned format.

## M3 — Deterministic evaluators and guardrails — not started

Add objective checks and a distinct enforcement interface.

Expected completion criteria:

- useful checks include exact/contains/regex and structured assertions where justified;
- evaluation outcomes distinguish pass, fail, error, and not applicable;
- guardrail decisions are separate from evaluator results;
- tests cover edge cases, invalid configuration, and evidence capture.

## M4 — Model-based evaluation — not started

Introduce semantic judging with structured outputs and explicit limitations.

Expected completion criteria:

- judge prompts and rubrics are versioned;
- judge outputs are validated and retain reasoning/evidence appropriate for audit;
- retries and malformed outputs are handled explicitly;
- a small human-labelled calibration set exposes agreement and disagreement;
- documentation addresses bias, variance, prompt sensitivity, and cost.

## M5 — Adversarial and red-team suite — not started

Build versioned cases for injection, leakage, unsafe compliance, refusal failures, and bypass attempts.

Expected completion criteria:

- cases have threat/risk labels and expected behavioural boundaries;
- both attacks and benign controls are present;
- results do not imply security guarantees;
- regression cases can be added from discovered failures.

## M6 — Risk policy, aggregation, and reporting — not started

Turn case-level evidence into transparent summaries and configurable decisions.

Expected completion criteria:

- aggregation handles missing/error outcomes without silently treating them as passes;
- policies use explicit thresholds and precedence rules;
- reports link aggregate metrics to case-level evidence;
- machine-readable and human-readable reports are generated from the same run data.

## M7 — Reproducibility, calibration, and hardening — not started

Strengthen experiment identity, reliability, and measurement confidence.

Expected completion criteria:

- runs capture code/config/dataset/model identifiers where available;
- judge variance and threshold sensitivity are examined;
- tests cover resume/failure behaviour and compatibility boundaries;
- a reproducibility guide demonstrates a clean repeat run.

## M8 — Results analysis and portfolio presentation — not started

Run real experiments and present defensible findings.

Expected completion criteria:

- published metrics come from retained run artefacts;
- findings distinguish observation from interpretation;
- README explains architecture, usage, results, limitations, and future work;
- an interview-ready walkthrough explains major decisions and trade-offs.

## M9+ — Advanced capabilities — deferred

Consider only with evidence of need: additional modalities, hosted execution, production telemetry, richer policy languages, or distributed runs.
