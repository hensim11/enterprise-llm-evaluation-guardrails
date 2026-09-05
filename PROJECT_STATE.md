# Project State

Last updated: 2026-09-05

## Current milestone

M2 — Provider-agnostic system interface and baseline runner: **complete**. Batch A crosses
parts of M3, M5, M6, and M8 and is **complete**: its empirical baseline gate and closeout
checks passed, and the reviewed change set is ready to commit. M3, M5, M6, and M8 remain
**in progress**; their remaining guardrail, regression, policy, interpretation, and
portfolio criteria are outside this batch.

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
- Literal, case-sensitive deterministic evaluation for schema-v1 `exact_match`, `contains`,
  and `not_contains`, without trimming, normalization, or semantic interpretation.
- Versioned evaluated-run schema `"1"` with pass, fail, error, and not-applicable semantics,
  per-assertion evidence, raw-execution-error propagation, round-trip validation, and exact
  run/fingerprint/case-order/status reconciliation. Persisted case outcomes and evidence
  must equal a canonical recomputation from the raw run.
- One reconciled aggregate feeding both summary JSON and Markdown, with explicit pass-rate
  and coverage denominators, undefined zero-denominator rates, per-risk-category results,
  an uncategorized bucket, and case-level raw/evaluated indices.
- Atomic offline and OpenAI output-directory workflows that refuse overwrite and never
  present a partially generated set as a completed experiment.
- An optional isolated OpenAI Responses API adapter with mandatory explicit model, standard
  environment credential loading, a versioned fictional-bank prompt/context formatter,
  completed-response enforcement, ordered extraction of output-text and refusal blocks,
  explicit rejection of malformed or unsupported message content, SDK retries explicitly
  disabled, `store=False`, fake-client offline tests, and explicit non-secret provenance
  including SDK version.
- A versioned 36-case fictional Northstar Bank benchmark with 38 honest literal assertions,
  eight risk categories, unsupported-claim traps, financial boundaries, privacy and
  injection attacks, and benign paired controls.

## Batch A closeout

- Batch A implementation, documentation, and one authorized paid baseline execution passed
  the review and validation gates. The four-file evidence package is retained under
  `evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/`.

## Verification

- Local interpreter: Python 3.14.0.
- Focused OpenAI adapter tests: 37 passed.
- Complete test suite: 201 tests collected and 201 passed.
- Ruff lint and format checks passed; `git diff --check` passed.
- The 36-case benchmark completed through the offline echo CLI and atomic evaluation
  workflow. All raw/evaluated joins and report indices were inspected programmatically;
  the persisted JSON summary exactly matched a newly derived aggregate, and credential
  markers were absent. Its echo outputs and metrics are synthetic plumbing evidence, not
  model measurements, and were not retained in the repository.
- The post-refusal-remediation 36-case offline run retained 36 ordered raw results and 36
  ordered evaluated results. Its JSON summary and Markdown report matched fresh canonical
  regeneration exactly, and its synthetic echo provider path made no network request.
- OpenAI SDK 1.66.0 is installed in the ignored local virtual environment. Its wheel was
  inspected for the Responses `create`, `store`, response status, ordered output-message
  structure, distinct output-text/refusal blocks, and client `max_retries` surfaces used
  here. Mocked tests prove ordered text/refusal preservation, malformed-content rejection,
  `max_retries=0`, `store=False`, completed-only success, and SDK-version provenance.
- One explicitly authorized run used `gpt-5.4-mini-2026-03-17`, SDK 1.66.0,
  `northstar-bank-assistant-v1`, `ordered-context-v1`, `max_retries=0`, `store=False`, and
  a maximum of 800 output tokens for each of 36 sequential application-level requests.
  The credential was supplied through the process environment and was not copied into
  source, configuration, logs, or evidence artefacts. No API key is stored in tracked
  project files or retained evidence.
- The paid baseline retained 36 ordered successful raw records and 36 ordered evaluated
  records for dataset fingerprint
  `6e6c9f92825f2ab266521180968f3eeb6341df7e0acd448916dac670bed0d698`.
  Canonical evaluated-evidence recomputation and exact JSON/Markdown regeneration passed.
  There were no execution errors, incomplete responses, or empty successful outputs.
- Measured literal outcomes were 29 pass, 2 fail, 0 error, and 5 not applicable at case
  level, and 36 pass, 2 fail, and 0 error across 38 assertions: a 94.74% deterministic
  assertion pass rate with 100% assertion-evaluation coverage. These are narrow surface-form
  measurements, not semantic correctness, robustness, privacy, safety, or security claims.
- Summed recorded request durations were 45.037322 seconds; individual durations ranged
  from 0.583229 to 3.077542 seconds with a 1.251037-second mean. The artefacts do not retain
  provider token usage, so actual token cost cannot be reconstructed from this evidence.
- No type checker is configured.
- Python 3.11 compatibility for the completed M2 code has not yet been executed locally or
  confirmed by CI; the workflow is configured to run the suite under Python 3.11.

## Not implemented

- guardrail enforcement;
- model-based or semantic evaluators;
- regex and richer deterministic checks;
- configurable risk policies or enforcement decisions;
- additional providers, application or SDK retries, concurrency, dashboards, databases, or
  hosted services.

## Known issues and risks

- The evaluation taxonomy and authored assertions will need review against real outputs.
- The 38 assertions measure literal surface properties only; five cases have no applicable
  deterministic assertion, and broader expected behaviours need future semantic evaluation.
- Schema migrations are not implemented. Unsupported versions fail explicitly so a
  future loader can add version dispatch when a second schema is justified.
- One 36-case empirical run exists, but a single finite run with literal assertions cannot
  establish model quality, robustness, safety, privacy, groundedness, or security beyond
  the recorded observations.
- Run artefacts intentionally retain complete case specifications, outputs, and error
  messages and may therefore require sensitive-data handling. Configuration safety is
  caller-controlled; there is no automatic secret detection or redaction.
- `store=False` minimizes Responses API application-state retention but does not disable
  provider abuse-monitoring retention or establish Zero Data Retention. The benchmark is
  synthetic; real customer data remains out of scope.
- Five successful cases have no deterministic assertions and remain explicitly not
  applicable rather than semantically assessed. The two deterministic failures are literal
  phrase mismatches and require interpretation alongside their case-level evidence.
- Provider content-block types are not retained in raw artefact schema v1, so the evidence
  preserves refusal-like output text but cannot establish whether the provider emitted a
  dedicated `refusal` block. The adapter behaviour is covered by SDK-shaped offline tests.
- Provider token usage is not retained, so actual cost cannot be reconstructed without an
  additional provider request, which was not authorized or made.
- Dataset fingerprints validate the current stored case snapshot and detect changes, but
  mutable retained metadata and on-demand calculation mean they are not immutable
  execution-time identities. They also do not prove source authenticity or make
  nondeterministic system responses reproducible.

## Recommended next objective

Deliver Batch B's matched guardrail-impact comparison on the unchanged 36-case benchmark.
Keep evaluation evidence distinct from runtime enforcement, use the retained Batch A run as
the comparison baseline, measure false refusals against benign controls, and follow the same
authorization and evidence-retention conventions for any paid execution.
