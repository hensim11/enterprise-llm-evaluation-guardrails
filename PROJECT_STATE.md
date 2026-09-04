# Project State

Last updated: 2026-09-04

## Current milestone

M1 — Evaluation-case schema and dataset loading: **complete**.

## Implemented

- Python package scaffold with a single version constant.
- Packaging metadata for Python 3.11+.
- Pytest and Ruff configuration.
- A small repository-contract test suite.
- Continuous-integration workflow for tests and linting.
- Project vision, roadmap, evaluation specification, and decision log.
- Evaluation-case schema version `"1"` with typed case and assertion objects.
- Strict validation for required and optional fields, supported values, unknown fields,
  non-null present fields, unique tags, unique assertion criteria, and JSON-compatible
  metadata. Validation applies through both mapping factories and exported typed
  constructors.
- UTF-8 JSONL loading that preserves source order and ignores blank lines.
- Actionable dataset errors with file, physical line, record, known case ID, and field
  context.
- Rejection of empty datasets, malformed JSON, unsupported versions, invalid records,
  duplicate JSON object keys, and duplicate case identifiers.
- Shallowly frozen case attributes with recursive defensive copies at metadata input
  and serialization boundaries; case-owned metadata remains mutable by design.
- A valid example dataset, valid and invalid test fixtures, and comprehensive boundary
  tests, including loading the documented example through the public API.

## In progress

Nothing. The repository is at a milestone boundary after M1.

## Verification

- Local interpreter: Python 3.14.0.
- Complete test suite: 79 tests collected and 79 passed.
- Ruff lint and format checks passed.
- `git diff --check` passed.
- No type checker is configured.

## Not implemented

- model/application provider interface;
- evaluation runner or run artefacts;
- deterministic or model-based evaluators;
- prompt-injection or red-team dataset;
- guardrail enforcement;
- risk policy engine, aggregation, or reports;
- model integrations or measured experiment results.

## Known issues and risks

- The evaluation taxonomy is an initial design and will need refinement against real cases.
- Schema v1 intentionally supports only three deterministic assertion shapes; their
  execution semantics remain M3 work.
- Schema migrations are not implemented. Unsupported versions fail explicitly so a
  future loader can add version dispatch when a second schema is justified.
- Python 3.11 baseline compatibility was not executed locally because Python 3.11 was
  unavailable. The inspected CI workflow is configured for Python 3.11, but it has not
  run against the current M1 commit.
- No empirical results exist, so the project cannot yet support claims about model quality or robustness.

## Recommended next objective

Implement the next narrow M2 increment: a minimal provider-agnostic system-under-test
protocol plus a deterministic test double. Do not add vendor SDKs, evaluators, scoring,
or guardrail enforcement.
