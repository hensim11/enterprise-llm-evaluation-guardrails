# Project State

Last updated: 2026-09-03

## Current milestone

M0 — Foundation and evaluation specification: **complete**.

## Implemented

- Python package scaffold with a single version constant.
- Packaging metadata for Python 3.11+.
- Pytest and Ruff configuration.
- A small repository-contract test suite.
- Continuous-integration workflow for tests and linting.
- Project vision, roadmap, evaluation specification, and decision log.

## In progress

Nothing. The repository is at a clean milestone boundary.

## Not implemented

- evaluation-case schema or dataset loader;
- model/application provider interface;
- evaluation runner or run artefacts;
- deterministic or model-based evaluators;
- prompt-injection or red-team dataset;
- guardrail enforcement;
- risk policy engine, aggregation, or reports;
- model integrations or measured experiment results.

## Known issues and risks

- The evaluation taxonomy is an initial design and will need refinement against real cases.
- No empirical results exist, so the project cannot yet support claims about model quality or robustness.
- CI is configured but will not have run until the repository is connected to a compatible Git hosting service.
- Development dependencies must be installed before the full test and lint commands can run.

## Recommended next objective

Implement M1: a minimal typed evaluation-case schema and a local JSONL dataset loader with explicit versioning and actionable validation errors.

Completion should include valid and invalid fixtures, unit tests for validation boundaries, a documented example case, and accurate updates to this file. Avoid adding model APIs or evaluators during M1.

