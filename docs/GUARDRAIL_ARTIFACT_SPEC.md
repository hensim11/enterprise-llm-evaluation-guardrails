# Guardrail Decision Artefact Schema v1

The guardrail decision artefact is the fourth evidence layer, separate from benchmark
specification, externally observed raw output, and deterministic evaluation evidence. Its
schema version is `"1"`.

## Top-level contract

The UTF-8 JSON object contains exact fields for schema version, source run identity,
policy identity/version, the complete ordered detector-version list, and ordered case
decisions. The source join contains raw run ID and dataset fingerprint. There must be
exactly one decision for each ordered raw-run case.

Every case decision repeats the policy and detector versions and records:

- case ID, used only after request-only enforcement has completed;
- ordered triggered detector IDs, versions, stages, decisions, and non-sensitive
  explanations;
- precedence-reduced final decision;
- whether the underlying model was invoked;
- whether a candidate response was released or replaced;
- a nullable SHA-256 candidate digest;
- whether observed raw output came from the underlying model, an input-block response, a
  response-block response, or an execution error;
- nullable replacement-response identity/version; and
- a canonical non-sensitive case explanation.

The artefact never stores the withheld candidate response. A digest is present for every
valid candidate, whether released or replaced; input blocks and invocation errors have no
candidate digest.

## Reconciliation

Loading optionally reconciles against the raw run. It requires exact run ID, fingerprint,
case order, policy version, detector versions, state combinations, and `BLOCK > WARN >
PASS` precedence. It reconstructs each `SystemRequest` from input and ordered context and
canonically reruns input detectors. Released candidate outputs are rechecked from raw
evidence. Versioned block-response text and explanation text must match exactly.

For a response block, the externally observed raw output contains only the fixed
replacement and the decision contains only the candidate digest. Consequently, the loader
can validate the canonical response trigger, replacement, state, and digest shape, but
cannot independently rerun the response match without separately retaining the withheld
candidate. This is an explicit evidence-minimization trade-off, not a security property.

Writers use exclusive creation. The atomic CLI stages all seven Batch B outputs and
publishes the directory with one rename only after every artefact and report validates.
