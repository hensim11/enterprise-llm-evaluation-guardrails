# Semantic Evaluation Artefact Specification

## Version and separation

Schema version `"1"` is a separate semantic-evaluation artefact. It does not extend or
rewrite raw-run schema v1 or deterministic evaluated-run schema v1. The artefact records
rubric, evaluator prompt, structured-output schema, source run, and judge identity.

Each result records the ordered case ID and raw-result index, raw execution status,
semantic outcome, confidence, rationale, exact response evidence, failure modes, semantic
duration, structured error, and provider token usage when supplied for a structurally
valid completed pass/fail judgement. Usage contains only provider-reported input, output,
and total token counts. No currency cost is inferred.

## Provenance and validation

The public loader rejects unsupported versions, duplicate JSON keys, unknown fields,
non-finite values, invalid enums, duplicate case IDs or indices, unknown or reordered
case/index joins, stale run IDs or dataset fingerprints, mismatched execution statuses,
fabricated excerpts, and invalid outcome/field combinations.

A semantic artefact can cover the complete raw run or an explicit non-empty subset, but a
subset must preserve raw-run order and identify every row by its original index. Raw
execution errors are copied as semantic `error` evidence without calling the judge. A
successful case with no expected behaviour is `not_applicable` without calling the judge.
Ordinary judge failures are isolated per case; interrupt and termination signals propagate.
Error and not-applicable rows are required to carry `usage=null`. If a provider call
consumed tokens but then failed or returned an incomplete or malformed response, usage may
be discarded before a valid judgement exists. Consequently, summed artefact usage can be
incomplete when judge errors are present and must not be described as total run usage.

The loader validates structure and provenance. It deliberately does not claim a canonical
recomputation of nondeterministic judge outcomes.

## Judge provenance

Core provenance is an explicit judge ID plus a caller-provided non-secret configuration
object. The OpenAI adapter allowlist records provider, API, installed SDK version, explicit
model, prompt version, output-schema version, maximum output tokens, `max_retries=0`, and
`store=false`. Credentials, environment values, `.env` content, and unrestricted client
state are never serialized by that adapter.

## Reporting denominators

Semantic pass rate is semantic passes divided by successfully judged pass-or-fail results.
Judgement coverage is pass-or-fail results divided by selected cases. Errors and
not-applicable results are reported separately and never counted as passes. Combined
reports expose raw execution, deterministic, semantic, human, and guardrail components
independently at overall, risk-category, and case levels; no composite score is emitted.
