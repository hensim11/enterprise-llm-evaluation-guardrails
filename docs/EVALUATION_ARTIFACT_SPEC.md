# Deterministic Evaluation Artefact Schema v1

This document defines the separate machine-readable evidence produced by the implemented
deterministic evaluator. Raw execution remains in run artefact schema v1; it is never
rewritten with pass/fail outcomes.

## Comparison semantics

All comparisons operate directly on Python strings using case-sensitive Unicode code-point
semantics:

- `exact_match`: `raw_output == configured_value`;
- `contains`: `configured_value in raw_output`; and
- `not_contains`: `configured_value not in raw_output`.

The evaluator does not trim whitespace, change case, normalize Unicode, parse markup,
rewrite punctuation, or infer meaning. An empty raw output is a valid successful execution
and is evaluated literally. Schema v1 requires assertion values to be non-empty.

These checks establish only the stated literal property. A passing substring check does
not by itself establish correctness, groundedness, safe behaviour, privacy, or injection
resistance.

## Top-level contract and joins

Evaluation artefacts are UTF-8 JSON objects with schema version `"1"`, a `source_run`, an
`evaluator`, and ordered `results`. `source_run` contains the raw run ID and dataset
fingerprint. The evaluator identity is `deterministic-string-assertions`, version `"1"`.

The loader validates exact fields, enum values, state combinations, unique case IDs, and
supported versions. Reconciliation against a raw run additionally requires an exact match
on:

1. run ID;
2. SHA-256 dataset fingerprint;
3. complete ordered case-ID sequence; and
4. each case's raw execution status.

Missing, duplicated, reordered, mismatched, malformed, and unsupported-version evidence is
rejected instead of joined heuristically. After those join checks, reconciliation calls the
same canonical `evaluate_run(raw_run)` implementation used to create evidence and requires
every stored case result—including outcome, assertion outcomes, explanations, and error
evidence—to match exactly. Shape-valid tampering cannot become trusted evaluated evidence.

## Case and assertion outcomes

Each case record contains `case_id`, copied `execution_status`, evaluation `outcome`, an
ordered assertion result array, and an explicit nullable `evaluation_error`.

- A successful execution with assertions evaluates every assertion. Each result retains
  criterion, assertion type, expected value, outcome, and a literal comparison explanation.
- The case is `pass` only when every assertion passes. It is `fail` when at least one
  assertion fails.
- A successful execution with no assertions is `not_applicable`.
- A raw execution error produces case outcome `error`, an explicit evaluation error, and
  one assertion-error record for every expected assertion. It never becomes a failed or
  passed assertion.

The writer uses exclusive file creation and never overwrites existing evidence.

## Aggregation

The implemented summary schema v1 reports execution counts, case-outcome counts, expected
and observed assertion counts, and results by risk category. An explicit `uncategorized`
bucket is always included, including when its count is zero. Every summary contains a
case-trace table with zero-based raw and evaluated result indices.

Rates are represented as `{numerator, denominator, value}`. `value` is JSON `null` when the
denominator is zero.

- **Assertion pass rate:** passed assertions / (passed + failed assertions). Assertion
  errors are excluded from this denominator and remain visible separately.
- **Assertion evaluation coverage:** (passed + failed assertions) / total expected
  assertions.
- **Deterministic case coverage:** cases with a pass-or-fail outcome / all cases.

The JSON summary and Markdown report are both generated from the same `AggregateReport`
mapping. No composite safety score, weighting scheme, threshold, or policy decision is
created. Persisted report validators compare the JSON mapping and Markdown rendering to a
fresh canonical aggregate exactly; changed counts or report text are rejected.
