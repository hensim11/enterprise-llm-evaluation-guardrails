# Roadmap

Status values: **complete**, **in progress**, **not started**. A milestone is complete only when its stated verification is satisfied.

## Delivery strategy from the M2 boundary

Milestones track capability status; they are not mandatory owner-review boundaries. From
the completed M2 boundary onward, work is delivered in bounded vertical batches that may
cross milestones when doing so produces a runnable, measurable outcome sooner.

The current fast-track sequence is:

1. first measured baseline: deterministic evaluation, minimum reporting, one real adapter,
   and an initial fictional-bank benchmark;
2. guardrail impact comparison on the same benchmark;
3. structured semantic evaluation with a small calibration set; and
4. reproducibility hardening and portfolio presentation.

See [`docs/DELIVERY_WORKFLOW.md`](docs/DELIVERY_WORKFLOW.md) for batch boundaries,
acceptance evidence, escalation rules, and the review gate. Milestone statuses below still
change only when their own criteria are satisfied.

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

## M3 — Deterministic evaluators and guardrails — in progress

Add objective checks and a distinct enforcement interface.

Delivered so far: literal exact-match, contains, and not-contains evaluation with explicit
outcomes and canonical evidence reconciliation, plus a separate versioned runtime guardrail
interface with PASS/WARN/BLOCK precedence, request/response detectors, block responses, and
decision evidence. Remaining milestone work includes regex or other justified evaluation
checks.

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

## M5 — Adversarial and red-team suite — in progress

Build versioned cases for injection, leakage, unsafe compliance, refusal failures, and bypass attempts.

Delivered so far: a versioned fictional-bank benchmark with adversarial cases, declared
benign pairs, risk labels, expected behaviours, narrow literal assertions, and one retained
real baseline result. Remaining milestone work includes a regression-case process informed
by discovered failures.

Expected completion criteria:

- cases have threat/risk labels and expected behavioural boundaries;
- both attacks and benign controls are present;
- results do not imply security guarantees;
- regression cases can be added from discovered failures.

## M6 — Risk policy, aggregation, and reporting — in progress

Turn case-level evidence into transparent summaries and configurable decisions.

Delivered so far: reconciled aggregation and shared machine/human evaluation reports, plus
matched guardrail comparison reports with explicit classification denominators, detector
counts/stages, configuration differences, transitions, case traces, workflow-derived replay
or fresh-provider attribution, and portable evidence references. Runtime guardrail
precedence is explicit; a general configurable risk-threshold policy remains unimplemented.

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

## M8 — Results analysis and portfolio presentation — in progress

Consolidate measured experiments into defensible findings and portfolio evidence. Real
experiments are pulled forward into the fast-track batches rather than deferred until M8.

Delivered so far: retained Batch A empirical evidence, reconciled deterministic metrics,
and a concise README summary linked to case-level evidence. Remaining work includes deeper
interpretation, final portfolio presentation, and an interview-ready walkthrough.

Expected completion criteria:

- published metrics come from retained run artefacts;
- findings distinguish observation from interpretation;
- README explains architecture, usage, results, limitations, and future work;
- an interview-ready walkthrough explains major decisions and trade-offs.

## M9+ — Advanced capabilities — deferred

Consider only with evidence of need: additional modalities, hosted execution, production telemetry, richer policy languages, or distributed runs.
