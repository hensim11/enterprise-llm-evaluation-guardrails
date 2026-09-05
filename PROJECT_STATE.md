# Project State

Last updated: 2026-09-05

## Current milestone

M2 — Provider-agnostic system interface and baseline runner: **complete**.

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
  metadata with finite numeric values. Validation applies recursively through both
  mapping factories and exported typed constructors.
- UTF-8 JSONL loading that preserves source order and ignores blank lines.
- Actionable dataset errors with file, physical line, record, known case ID, and field
  context.
- Rejection of empty datasets, malformed JSON, unsupported versions, invalid records,
  duplicate JSON object keys, and duplicate case identifiers.
- Shallowly frozen case attributes with validation and recursive defensive copies at
  metadata input and serialization boundaries. Case-owned metadata remains mutable by
  design, and invalid mutations are rejected when `to_mapping()` is called.
- A valid example dataset, valid and invalid test fixtures, and comprehensive boundary
  tests, including loading the documented example through the public API.
- A synchronous, provider-agnostic `SystemUnderTest` structural protocol with immutable,
  typed request and response values and no runtime dependencies.
- A deliberately simple deterministic echo test double that returns input text verbatim
  and does not claim to simulate intelligence, domain correctness, or safety.
- An explicit system-input boundary: only input text and ordered supplied context enter
  the request; case identity and evaluation-only expectations remain outside it.
- Documented failure semantics: the baseline runner isolates ordinary per-case system
  exceptions, while an empty string remains a valid observable response.
- A sequential baseline runner that loads and snapshots the complete validated dataset,
  sends only input and ordered context to the system, and records exactly one ordered
  execution result per case in a normally completed run.
- Per-case isolation for ordinary system exceptions and response-contract violations,
  with continued execution, monotonic durations in seconds, structured error details,
  and explicit null output on error. Interrupt and termination signals still propagate.
- Versioned run artefact schema `"1"` with run and system identity, an explicit
  non-secret system-configuration allowlist, dataset source, complete ordered case
  snapshot, canonical SHA-256 fingerprint, and validated round-trip JSON I/O.
- Artefact provenance rejects duplicate case IDs during direct construction and loading,
  preserving unambiguous case-to-result joins.
- Response output access and string validation occur inside the per-case exception
  boundary, so malformed response subclasses cannot prevent later cases from running.
- A local CLI using the deterministic echo double for synthetic plumbing demonstrations
  without network access or provider credentials.
- Documentation for runner invocation, data flow, execution/error semantics, artefact
  fields, fingerprint construction, confidentiality, and reproducibility limitations.

## In progress

Nothing. The repository is at a milestone boundary after M2.

## Verification

- Local interpreter: Python 3.14.0.
- Focused runner regression and artefact-validation tests: 24 tests collected and 24
  passed.
- Complete test suite: 130 tests collected and 130 passed.
- Ruff lint and format checks passed.
- `git diff --check` passed.
- The documented synthetic echo CLI demonstration completed with two ordered results;
  its generated artefact was inspected and loaded through the public artefact reader.
- No type checker is configured.
- Python 3.11 compatibility for the completed M2 code has not yet been executed locally or
  confirmed by CI; the workflow is configured to run the suite under Python 3.11.

## Not implemented

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
- No empirical results exist, so the project cannot yet support claims about model quality or robustness.
- Run artefacts intentionally retain complete case specifications, outputs, and error
  messages and may therefore require sensitive-data handling. Configuration safety is
  caller-controlled; there is no automatic secret detection or redaction.
- Dataset fingerprints validate the current stored case snapshot and detect changes, but
  mutable retained metadata and on-demand calculation mean they are not immutable
  execution-time identities. They also do not prove source authenticity or make
  nondeterministic system responses reproducible.

## Recommended next objective

Deliver Batch A — First measured baseline, as defined in
`docs/DELIVERY_WORKFLOW.md`. Build from the completed M2 runner to execute the existing
deterministic assertions, add the minimum traceable aggregation/reporting path, introduce
one real provider adapter, author the initial fictional-bank benchmark, and produce a real
retained baseline run. Keep evaluator evidence separate from execution status and exclude
guardrail enforcement and model-based judging from this batch.
