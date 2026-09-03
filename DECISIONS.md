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

