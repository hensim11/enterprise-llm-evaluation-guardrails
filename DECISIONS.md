# Decision Log

Only architectural or methodological decisions belong here. Implementation detail should remain near the code.

## ADR-001 — Start as a local-first Python library and CLI

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Build the core as a Python 3.11+ package with local file artefacts. Add a small CLI when the runner exists. Do not introduce a web service, database, or orchestration framework initially.
- **Rationale:** Evaluation work benefits from Python's ML ecosystem, while local files make early experiments inspectable and reproducible. Services would add operational complexity before requirements justify it.
- **Consequences:** Early use is developer-oriented and single-machine. Interfaces should remain suitable for later wrapping without designing a distributed platform in advance.

## ADR-002 — Separate evaluation evidence from guardrail enforcement

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Evaluators return observations, scores, and evidence. A separate policy/enforcement layer turns those results or runtime detector signals into allow, block, redact, review, or error decisions.
- **Rationale:** Measurement and intervention answer different questions. Combining them would obscure results, complicate calibration, and make policy changes look like evaluator changes.
- **Consequences:** Shared detectors may require adapters, but evaluator results and enforcement decisions need distinct types and audit trails.

## ADR-003 — Use complementary evaluation methods

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Prefer deterministic checks and structured assertions where possible; use model-based judges only for properties that need semantic judgement. Preserve individual evaluator outcomes rather than relying solely on a composite score.
- **Rationale:** No single method covers correctness, groundedness, safety, and instruction following reliably. Deterministic checks are reproducible but narrow; judges are flexible but noisy.
- **Consequences:** Reports will be more detailed, and aggregation must handle heterogeneous outcomes and missing evidence explicitly.

## ADR-004 — Version external data contracts from their first implementation

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Evaluation datasets and run artefacts must include an explicit schema version when introduced.
- **Rationale:** Cases and results are long-lived evidence. Explicit versions make compatibility changes detectable and reproducible.
- **Consequences:** Loaders must reject unsupported versions clearly, and migrations may eventually be required.

## ADR-005 — Preserve honest milestone boundaries

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Documentation must distinguish implemented capability, planned work, and illustrative examples. A milestone is complete only when its verification criteria pass.
- **Rationale:** The project is intended to demonstrate engineering and governance judgement. Inflated status claims undermine both.
- **Consequences:** Early README sections may describe substantial target capability while prominently stating that runtime features are not yet implemented.

## ADR-006 — Keep evaluation-case schema v1 strict and dependency-free

- **Date:** 2026-09-03
- **Status:** accepted
- **Decision:** Version every serialized case with the exact string `"1"`. Validate it
  with small typed Python domain objects and explicit project code rather than adding a
  schema library. Reject unknown top-level and assertion fields, while permitting
  JSON-compatible values inside the explicit `metadata` object. Ignore blank JSONL
  lines but reject files with no applicable records. Keep case attributes shallowly
  frozen and defensively copy metadata at input and serialization boundaries; do not
  introduce a custom recursively immutable JSON representation at M1.
- **Rationale:** The first schema is small enough for direct validation, and the project
  has no runtime dependencies. Strict fields and no coercion expose misspellings and
  incompatible data early. A metadata boundary permits provenance without weakening
  the behavioural contract. Per-record versioning allows a future loader to dispatch
  versions without building migration machinery before a second version exists.
  Shallow freezing preserves ordinary JSON dictionaries and lists for downstream code
  while defensive copying prevents accidental mutation of caller-owned data.
- **Consequences:** Authors receive deterministic field-level errors and datasets remain
  reproducible, but additions to the behavioural contract require a schema-version
  decision. Blank lines can be used for readability and do not affect record numbering;
  errors report both physical line and applicable-record positions. Consumers may
  mutate case-owned metadata in place, so the case type must not be described as deeply
  immutable. Serialization revalidates the current mutable metadata while recursively
  copying it, so invalid mutations cannot escape through `to_mapping()`.

## ADR-007 — Keep system inputs separate from evaluation expectations

- **Date:** 2026-09-04
- **Status:** accepted
- **Decision:** The provider-agnostic system request contains only input text and ordered
  supplied context. Case identity, references, assertions, expected behaviour, risk
  labels, tags, and arbitrary metadata remain in the evaluation layer. Systems implement
  a synchronous structural protocol and return raw output text; an empty string is a
  valid output. Ordinary implementation exceptions propagate to the caller.
- **Rationale:** A system should receive only the information it would be given during
  execution. Supplying evaluation expectations would contaminate the observation and
  couple adapters to the dataset schema. Structural typing keeps application and model
  integrations independent of a concrete test double or vendor SDK.
- **Consequences:** A runner must explicitly construct each request while retaining case
  identity and expectations separately. It must also isolate and record per-case
  exceptions without converting them to successful responses. Response validation can
  distinguish an observed empty output from an invalid non-string adapter result.

## ADR-008 — Preserve raw runs as validated case snapshots plus execution evidence

- **Date:** 2026-09-04
- **Status:** accepted
- **Decision:** Store each completed baseline run as one versioned UTF-8 JSON object with
  run and system identity, an explicit non-secret configuration allowlist, the complete
  ordered validated case snapshot and its canonical SHA-256 fingerprint, and exactly one
  ordered raw execution result per case. Use only `success` and `error` execution states;
  do not add evaluation outcomes. Catch ordinary per-case exceptions while allowing
  `BaseException` subclasses to propagate.
- **Rationale:** The snapshot keeps case specifications reconstructable without exposing
  evaluation-only fields to the system. A fingerprint makes changes detectable without
  treating a source path as content identity. Explicit null output on error distinguishes
  failure from a valid empty response. An allowlist avoids introspecting adapters and
  accidentally serializing credentials.
- **Consequences:** Artefacts are intentionally verbose and may contain sensitive cases,
  outputs, or error messages, so they require appropriate handling and must not be
  committed by default. Fingerprints detect snapshot changes but do not prove source
  authenticity or guarantee repeatable model responses. Because retained case metadata
  is mutable and fingerprints are calculated on demand, the fingerprint validates the
  current stored snapshot rather than establishing immutable execution-time identity.
  Sequential execution is simple and traceable but does not optimize throughput.

## ADR-009 — Use literal deterministic semantics and separately joined evidence

- **Date:** 2026-09-05
- **Status:** accepted
- **Decision:** Execute schema-v1 assertions with unmodified, case-sensitive Python string
  equality and membership. Store results in a separate versioned evaluation artefact joined
  to raw evidence by run ID, dataset fingerprint, ordered case ID, and execution status.
  Aggregate pass rate only over pass/fail assertions, while reporting evaluation coverage,
  execution errors, non-applicable cases, and zero denominators explicitly. Render JSON and
  Markdown from one aggregate representation.
- **Rationale:** Literal operations are reproducible and auditable, while normalization or
  semantic interpretation would silently change the assertion contract. Strong joins stop
  stale or partial evidence from being combined. Separate denominators prevent unavailable
  evidence from improving apparent results.
- **Consequences:** Surface-form variation can fail otherwise acceptable answers, and many
  important behaviours remain unmeasured until semantic evaluation exists. The reports are
  intentionally detailed and do not produce a composite safety score or policy decision.

## ADR-010 — Isolate one explicit OpenAI baseline configuration

- **Date:** 2026-09-05
- **Status:** accepted
- **Decision:** Implement one optional OpenAI adapter with the official Python SDK and
  Responses API behind `SystemUnderTest`. Require the model ID, version the fictional-bank
  instructions and ordered-context formatter, and serialize only an explicit non-secret
  provenance allowlist including the installed SDK version. Require a completed top-level
  provider status before accepting output, construct the SDK client with `max_retries=0`,
  and send `store=False` on every request. Constrain the optional dependency to the verified
  compatible range `openai>=1.66.0,<3.0`. Publish multi-file workflows through a temporary
  sibling directory and one final rename.
- **Rationale:** One real adapter enables measurement without coupling the core to a vendor
  or creating a premature provider framework. Explicit model and prompt identity make the
  baseline interpretable. Atomic publication prevents a partial output set from looking like
  a completed experiment.
- **Consequences:** The optional provider dependency and credentials are needed only for a
  real run. There are deliberately no application-level or SDK retries, concurrency,
  hidden model selection, or fallback. The 36-case workflow therefore makes 36
  application-level calls when every case is attempted; disabling SDK retries prevents
  SDK-added HTTP retry attempts but does not characterize lower network layers. Setting
  `store=False` minimizes Responses application-state retention but does not eliminate
  default abuse-monitoring retention or establish Zero Data Retention. Prompt instructions
  are system behaviour under test, not separate guardrail enforcement or a security
  guarantee.

## ADR-011 — Enforce at the request boundary and retain separate matched evidence

- **Date:** 2026-09-06
- **Status:** accepted
- **Decision:** Wrap the provider-neutral system with a versioned runtime policy that sees
  only input and ordered context and, after invocation, the candidate response. Use explicit
  `BLOCK > WARN > PASS` precedence. Represent blocks as successful versioned observed
  outputs, keep every guardrail decision in a separate versioned artefact, and compare it
  only with raw/evaluated runs having the same fingerprint and ordered case IDs. Retain a
  digest rather than the withheld response candidate. Persist a workflow-derived
  deterministic-replay or fresh-provider comparison mode with mode-specific attribution,
  and identify evidence through typed bundle-relative or repository-relative references.
- **Rationale:** A wrapper preserves the existing system contract and raw/evaluated schemas
  while making invocation avoidance and response replacement observable. Separate evidence
  prevents enforcement from becoming an evaluation outcome. Strict matched-run comparison
  stops dataset drift from being presented as guardrail impact. Candidate minimization
  avoids copying detected secrets into decision evidence.
- **Consequences:** Input decisions can be canonically recomputed from the stored case
  request, and released outputs can be rechecked. For response blocks, the loader can verify
  the canonical trigger/state/replacement and digest shape but cannot independently rerun
  the response match without the intentionally unretained candidate. Policy v1 is a narrow
  benchmark-justified phrase/regex system, not semantic understanding, redaction, a broad
  PII catalogue, or a security guarantee. Replay can attribute differences to guardrail and
  deterministic evaluation treatment of retained candidates. Fresh-provider deltas beyond
  input-block invocation avoidance remain observational because model/provider
  nondeterminism can contribute. Comparison evidence is portable across machines when its
  declared bundle or repository base is preserved; unrelated external baseline locations
  are rejected rather than serialized as absolute paths.

## ADR-012 — Judge authored expected behaviour with a binary case outcome

- **Date:** 2026-09-07
- **Status:** accepted
- **Decision:** A completed semantic judgement is `pass` or `fail` against the case's
  authored expected behaviour, context, references, risk category, and tags. Surface form
  alone does not decide the result. Errors and genuinely undefined expectations remain
  explicit, and audit excerpts must be exact retained-output substrings.
- **Rationale:** A narrow binary question is inspectable on a small calibration set and
  avoids inventing an unjustified continuous quality scale.
- **Consequences:** The rubric cannot express degrees of quality. Confidence describes
  rubric application only and must not be interpreted as system safety confidence.

## ADR-013 — Retain semantic evidence separately from deterministic evaluation

- **Date:** 2026-09-07
- **Status:** accepted
- **Decision:** Store semantic results in their own versioned artefact, joined to raw
  evidence by run ID, fingerprint, case ID, raw index, and execution status. Validate
  structure and provenance but do not claim canonical recomputation of nondeterministic
  judge outcomes.
- **Rationale:** Semantic judgement has different evidence, failure, cost, and
  reproducibility properties from literal assertions.
- **Consequences:** Reports must reconcile multiple components explicitly and retain more
  files, while existing schema-v1 raw and deterministic evidence remains unchanged.

## ADR-014 — Treat challenge-weighted calibration labels as diagnostics, not estimates

- **Date:** 2026-09-07
- **Status:** accepted
- **Decision:** Fix 12 source-ordered cases before labelling: all five deterministic N/A
  cases, all three deterministic failures, and four stratified benign/adversarial cases.
  Do not infer or prefill owner labels and do not treat the subset as representative.
- **Rationale:** The set concentrates the semantic gaps and known literal disagreements
  most useful for judge review within a small paid run.
- **Consequences:** Agreement on the subset is challenge-weighted diagnostic evidence and
  cannot be generalized as full-run judge accuracy or system performance.

## ADR-015 — Report exact small-sample agreement and confusion counts

- **Date:** 2026-09-07
- **Status:** accepted
- **Decision:** Use exact agreement, disagreements, judge errors, coverage, and all four
  binary human/judge confusion counts. Exclude judge errors from agreement denominators
  while keeping them visible. Do not add kappa-like or composite metrics at this size.
- **Rationale:** Direct counts are understandable and proportionate for 12 deliberately
  selected examples; more elaborate statistics would imply unsupported precision.
- **Consequences:** Every disagreement requires qualitative inspection and classification;
  the human label remains a calibration reference rather than universal truth.

## ADR-016 — Disclose label blinding and require provenance-bound disagreement review

- **Date:** 2026-09-07
- **Status:** accepted
- **Decision:** Record whether completed human labels were blinded to deterministic
  outcomes and selection reasons. Preserve the completed Batch C owner labels as partially
  unblinded because the original worksheet exposed both. Future worksheets omit those
  fields. Before calibration is eligible for owner acceptance, require one classified,
  rationalized review for every human/judge disagreement in a strict artefact bound to the
  semantic evidence and human labels.
- **Rationale:** Annotation context can influence labels and must remain visible. A durable
  exhaustive review gate prevents unresolved disagreements from being hidden in aggregate
  agreement while protecting reviews from accidental reuse with changed evidence.
- **Consequences:** The completed labels remain valid diagnostic evidence with an explicit
  limitation. Calibration needs an extra review artefact whenever disagreement exists;
  changing source evidence invalidates that review, and owner acceptance remains separate.
