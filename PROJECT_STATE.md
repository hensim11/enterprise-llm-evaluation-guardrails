# Project State

Last updated: 2026-09-07

## Current milestone

M2 — Provider-agnostic system interface and baseline runner: **complete**. Batch A is
complete and committed in `7b120426`. Batch B's implementation is committed in `d72205b`.
Batch B is **complete**: its authorized fresh-provider run passed inspection and its
seven-file evidence package is retained in the repository. M3, M5, M6, and M8 remain **in
progress**. Batch C and M4 are **in progress**: implementation and all 12 completed owner
labels are ready, but authorized real judge evidence and accepted calibration do not yet
exist.

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
- A request-only runtime wrapper that exposes only input and ordered context to input
  guardrails and additionally the candidate response to response guardrails; case IDs and
  all evaluation-only fields are attached after enforcement.
- Northstar runtime guardrail policy version `"1"` with explicit `BLOCK > WARN > PASS`
  precedence; narrow authentication-disclosure, financial-directive, hidden-prompt,
  override-indicator, and response-leakage detectors; and versioned block responses.
- Input blocks that avoid underlying invocation while producing successful externally
  observed raw output, and response blocks that withhold and replace a candidate without
  turning either policy action into an execution error.
- Versioned guardrail-decision artefact schema `"1"` with policy/detector versions,
  triggers/stages, invocation/release/replacement state, non-sensitive explanations,
  candidate digests, strict raw joins, and canonical validation.
- Versioned matched-comparison schema `"1"` with complete configuration identity and
  differences, guardrail decision/trigger counts, avoided invocations, deterministic
  deltas/transitions, narrow benign false-refusal measurement, separate benign warnings,
  adversarial decisions, unclassified cases, and complete case traces.
- Workflow-derived `deterministic_replay` and `fresh_provider_execution` comparison modes
  with machine-readable and Markdown attribution. Replay uses the same retained candidates;
  fresh-provider PASS/WARN outputs and resulting deltas are explicitly observational and
  potentially confounded, while input-block invocation avoidance is directly attributable.
- Typed portable evidence references resolve from the comparison bundle or repository root;
  machine-specific absolute paths and unrelated external baseline locations are rejected.
- Atomic replay and OpenAI guardrailed CLI workflows producing raw/evaluated evidence,
  ordinary JSON/Markdown reports, decisions, and machine/human comparison reports.
- Semantic rubric `authored-expected-behaviour` version `1`, with binary completed
  judgements, explicit confidence semantics, exact response excerpts, and enumerated
  material failure modes.
- A synchronous provider-neutral semantic judge protocol and sequential full/subset
  evaluator that preserves raw errors, uses N/A only for absent expected behaviour,
  isolates ordinary judge failures, and propagates interrupts.
- Separate semantic artefact schema `1` with rubric/prompt/output-schema versions, strict
  raw provenance and ordered-index joins, explicit errors and durations, optional
  provider-supplied token usage for valid completed judgements, and honest non-canonical
  validation. Judge-error usage can be unavailable even when a failed call consumed tokens.
- An optional OpenAI Responses semantic judge with required explicit model, strict JSON
  schema, independent parsing, completed-response enforcement, SDK retries disabled,
  storage disabled, and exhaustive non-secret provenance.
- A fixed, pre-label, source-ordered 12-case challenge-weighted calibration selection,
  12 strict completed owner labels (8 pass, 4 fail), an explicit partial-unblinding record,
  a future blinded worksheet, completed human-label schema, agreement/confusion analysis,
  and exact shared-data JSON/Markdown rendering.
- A strict disagreement-review artefact bound to canonical semantic and human-label
  evidence. Calibration becomes eligible for owner acceptance only with full pass/fail
  judgement coverage, zero judge errors, and every disagreement classified and rationalized.
- Versioned combined semantic reporting with separate raw execution, deterministic,
  semantic, human-label, runtime-guardrail, and provider-error fields and denominators.

## Batch A closeout

- Batch A implementation, documentation, and one authorized paid baseline execution passed
  the review and validation gates. The four-file evidence package is retained under
  `evidence/baselines/northstar-v1-gpt-5.4-mini-2026-03-17-20260905/`.

## Batch B closeout

- Batch B implementation, documentation, one authorized 27-request provider execution,
  artefact inspection, and relocation validation passed the acceptance gates. The unchanged
  seven-file evidence package is retained under
  `evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/`.

## Verification

- Local interpreter: Python 3.14.0.
- Batch C focused semantic, calibration, OpenAI-judge, reporting, and CLI tests: 64 passed.
- Complete suite after acceptance-gate remediation: 294 tests collected and 294 passed.
- Ruff lint and format checks and `git diff --check` passed after the final implementation
  changes.
- The fixed calibration workflow generated 12 ordered cases at raw indices 5, 8, 14, 16,
  19, 20, 21, 22, 26, 27, 28, and 31. The completed-label loader validated the exact
  retained run ID, fingerprint, case/index order, 8-pass/4-fail labels, and all non-empty
  owner rationales. The artefact records that the original worksheet partially unblinded
  the owner to deterministic outcomes and selection reasons. A separately generated future
  worksheet omits both fields.
- A deterministic offline fake judge exercised all 12 selected retained outputs with zero
  network calls. The semantic artefact reloaded through the public strict loader; the
  combined JSON and Markdown regenerated exactly; raw execution, deterministic, and fake
  semantic component counts reconciled to all 12 case traces. The calibration CLI emitted
  four disagreement drafts for the all-pass fake, rejected incomplete review evidence, and
  accepted a completed provenance-bound four-row review in a second report. These fake
  outcomes are workflow evidence only and are not retained or reported as model
  measurements.
- Focused OpenAI adapter tests: 37 passed.
- Complete test suite: 230 tests collected and 230 passed.
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
- The explicitly authorized Batch A baseline used `gpt-5.4-mini-2026-03-17`, SDK 1.66.0,
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
- Batch B focused tests demonstrate request-only detector inputs, input-block invocation
  avoidance with a counting fake, response replacement with deliberately leaking fake
  outputs, exact artefact joins, canonical tamper rejection, classification denominators,
  matched transitions, both comparison modes and their attribution boundaries, portable
  resolvable evidence references, external-location rejection, and seven-file CLI
  publication.
- The full 36-case deterministic replay against retained Batch A outputs preserved the
  required fingerprint and produced exactly 36 successful observed raw outputs and 36
  decisions: 24 PASS, 3 WARN, and 9 BLOCK, with 9 replay invocations avoided. Benign false
  refusals were 0/18 and benign warnings were 0/18. Adversarial decisions were 8 BLOCK, 3
  WARN, and 2 PASS; five cases were unclassified. Literal assertions changed from 36 pass / 2
  fail to 35 pass / 3 fail. These are inspected synthetic replay results, not a new provider
  measurement. The regenerated comparison declared `deterministic_replay`, retained no
  machine-specific absolute paths in JSON or Markdown, and all five evidence references
  resolved from their declared repository or bundle bases.
- One explicitly authorized Batch B run used `gpt-5.4-mini-2026-03-17`, SDK 1.66.0,
  `northstar-bank-assistant-v1`, `ordered-context-v1`, `max_retries=0`, `store=False`, and
  a maximum of 800 output tokens. Nine deterministic input blocks limited the run to 27
  sequential application-level provider requests. All 27 completed; there were no
  provider execution errors, application retries, SDK retries, fallbacks, or additional
  attempts. The complete atomically published bundle is retained unchanged under
  `evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/`.
- The empirical bundle contains 36 successful externally observed raw results, 36
  guardrail decisions, 36 deterministic case results, 38 assertion results, and 36
  comparison trace rows for the unchanged fingerprint. Guardrail decisions were 24 PASS,
  3 WARN, and 9 BLOCK. All nine blocks were input-stage blocks, so nine provider
  invocations were directly avoided; the response-leakage detector triggered zero times
  and no candidate response was withheld or replaced.
- Empirical deterministic outcomes were 28 pass, 3 fail, 0 error, and 5 not applicable at
  case level, with 35 pass, 3 fail, and 0 error across 38 assertions (92.1% assertion pass
  rate and 100% assertion-evaluation coverage). Against the retained baseline this is one
  fewer pass and one more fail at both case and assertion level: 28 pass→pass, one
  pass→fail, two fail→fail, and five not-applicable→not-applicable transitions. The new
  pass→fail is the directly input-blocked unclassified mortgage-eligibility case; the
  fraud-refund and password-safety literal failures were already present in the baseline.
- Empirical benign false refusals were 0/18 and benign warnings were 0/18. Adversarial
  decisions were 8 BLOCK, 3 WARN, and 2 PASS; five cases were unclassified. These are
  policy observations, not an accuracy score. Of the 27 released provider outputs, 21
  differed textually from their retained baseline counterparts despite unchanged aggregate
  literal outcomes for provider-invoked cases, illustrating the documented nondeterminism
  confound.
- Canonical loaders and render validators accepted all seven empirical files. The
  comparison declared `fresh_provider_execution`, separated directly attributable
  input-block avoidance from observational/confounded PASS/WARN outputs and deltas, and
  used five resolving portable evidence references. Direct screening found no credential
  value or name, local username, `.env` reference, absolute filesystem path, or generic API
  key pattern in the bundle.

## Not implemented

- an authorized real model-based judge run, completed disagreement inspection, accepted
  calibration evidence, or the full 36-case semantic measurement;
- regex and richer deterministic checks;
- a general configurable risk-threshold language beyond the explicit Northstar policy;
- additional providers, application or SDK retries, concurrency, dashboards, databases, or
  hosted services.

## Known issues and risks

- The evaluation taxonomy and authored assertions will need review against real outputs.
- The 38 assertions measure literal surface properties only; five cases have no applicable
  deterministic assertion. The semantic path can measure broader expected behaviours, but
  it has not yet produced authorized real-judge evidence.
- The completed calibration labels were partially unblinded because the original worksheet
  exposed deterministic outcomes and selection reasons. This is retained as a limitation;
  future worksheets hide both fields.
- Schema migrations are not implemented. Unsupported versions fail explicitly so a
  future loader can add version dispatch when a second schema is justified.
- Two 36-case empirical provider runs are retained: the Batch A baseline and Batch B
  guardrailed comparison. These finite runs and literal assertions cannot establish model
  quality, robustness, safety, privacy, groundedness, or security beyond the recorded
  observations.
- Run artefacts intentionally retain complete case specifications, outputs, and error
  messages and may therefore require sensitive-data handling. Configuration safety is
  caller-controlled; there is no automatic secret detection or redaction.
- `store=False` minimizes Responses API application-state retention but does not disable
  provider abuse-monitoring retention or establish Zero Data Retention. The benchmark is
  synthetic; real customer data remains out of scope.
- In the baseline, two of 38 assertions failed. In the guardrailed run, three of 38 failed:
  the same fraud-refund and password-safety literal phrase mismatches plus the
  `unsupported-mortgage-eligibility` pass→fail transition caused by its input-block text.
  Five successful cases in each run have no deterministic assertions and remain explicitly
  not applicable rather than semantically assessed.
- Provider content-block types are not retained in raw artefact schema v1, so the evidence
  preserves refusal-like output text but cannot establish whether the provider emitted a
  dedicated `refusal` block. The adapter behaviour is covered by SDK-shaped offline tests.
- Provider token usage is not retained for either empirical run, so their actual costs
  cannot be reconstructed from the evidence.
- Semantic judge usage is retained only on structurally valid completed judgements. A call
  that consumed tokens but ended in a provider, incomplete-response, or parsing error may
  have `usage=null`, so totals are potentially incomplete whenever judge errors exist.
- Dataset fingerprints validate the current stored case snapshot and detect changes, but
  mutable retained metadata and on-demand calculation mean they are not immutable
  execution-time identities. They also do not prove source authenticity or make
  nondeterministic system responses reproducible.
- Guardrail v1 uses narrow regex, phrase, labelled-value, canary, and digit-shape matching.
  It can produce false positives and can be bypassed; it is not semantic understanding,
  broad PII detection, redaction, or a security guarantee.
- Withheld response candidates are represented only by SHA-256 digests. This minimizes
  copied sensitive evidence but prevents independent canonical replay of a response-block
  match without separately retaining the candidate.
- The deterministic replay isolates policy effects over retained outputs but is not a fresh
  provider run and cannot measure new model/guardrail interaction or nondeterminism.
- The inspected fresh-provider comparison directly attributes avoided invocations to input
  blocks, but its PASS/WARN outputs, outcome transitions, and metric deltas can also reflect
  provider/model nondeterminism and remain labelled observational. The artefacts do not
  include transport logs or a retry counter; the no-SDK-retry claim is grounded in the
  committed adapter's `max_retries=0` construction and the verified live client setting.
- Batch B BLOCK results are policy-decision observations, not semantic correctness scores.
  In particular, the gambling-harm and tax-evasion cases receive the generic financial
  decision block response, which does not fully satisfy their authored expectations to
  address harmful escalation, suggest support, or direct the user to qualified help.
  Semantic evaluation of block-response quality belongs to Batch C and is not yet measured.

## Recommended next objective

Obtain separate authorization for the explicit model and paid 12-call calibration judge
run. Then produce the combined and calibration reports, classify and rationalize every
human/judge disagreement, and obtain owner acceptance. Do not proceed to the full 36-case
semantic measurement before that acceptance.
