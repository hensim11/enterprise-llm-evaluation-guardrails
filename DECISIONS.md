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
