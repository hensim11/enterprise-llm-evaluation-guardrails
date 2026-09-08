# Batch D Contract — Reproducibility and Portfolio Release

## Objective

Make the retained Batch A, B, and C system evidence straightforward for a reviewer to
clone, install, validate offline, inspect, and explain. Batch D packages and verifies
existing capabilities and measurements; it does not add evaluation or enforcement
behaviour or produce new empirical outcomes.

## In scope

- One documented, credential-free repository command that loads retained raw,
  deterministic, guardrail, comparison, semantic, calibration, disagreement-review,
  human-label, and owner-acceptance artefacts through public APIs; canonically regenerates
  all derived JSON and Markdown reports in temporary storage; and fails clearly on drift.
- Automated success and controlled stale/tampered-report failure coverage without changing
  retained evidence.
- Python 3.11+ CI coverage through the repository's currently verified interpreter where
  practical, plus wheel build/install and an installed CLI smoke test from outside the
  checkout.
- A copy-pasteable reproducibility guide, an interview-ready portfolio walkthrough, and a
  concise GitHub landing page grounded in retained evidence.
- Evidence-backed updates to project state and roadmap status after all acceptance checks
  pass.

## Exclusions

- Provider or paid API calls, new measurements, benchmark cases, detectors, guardrail
  policies, evaluator types, semantic rubrics, or threshold machinery.
- Retry, resume, concurrency, dashboards, services, databases, second providers,
  judge-variance experiments, or prompt-sensitivity experiments.
- Unrelated refactoring, changes to declared Python support, or edits to retained empirical
  evidence.
- Claims of general accuracy, safety, security, judge accuracy, or provider-response
  reproducibility.

## Acceptance evidence

- The single offline command verifies every applicable retained Batch A/B/C artefact,
  regenerates canonical reports in temporary storage, compares them byte-for-byte with the
  retained reports, and prints verified bundle names plus reconciled counts.
- Tests demonstrate a complete successful verification and rejection of a deliberately
  stale or altered derived report without mutating retained evidence.
- A wheel builds, installs into an isolated environment, and its CLI succeeds from outside
  the repository; CI covers supported Python versions from 3.11 through the current
  practical verified version while keeping the OpenAI SDK optional.
- The full test suite, Ruff lint, Ruff format check, and `git diff --check` pass.
- Every new documentation link and command is exercised; retained evidence is byte-for-byte
  unchanged; and README, project state, roadmap, reproducibility guide, and walkthrough
  agree on capabilities, findings, and limitations.

## Validation approach

Record a pre-change digest manifest for tracked retained evidence. Exercise the repository
verifier both directly and via tests, run packaging checks in fresh temporary environments,
run the complete quality suite, check documentation links/commands, and compare final
evidence digests with the manifest. Derive every published count from strict loaded
artefacts rather than transcribing unsupported claims.

## Stop conditions

Stop and request owner direction only if completion would require changing a published
metric, modifying retained evidence, making a provider call, changing Python-support
policy, or materially expanding architecture or scope. Resolve ordinary implementation,
test, lint, packaging, and documentation failures within this batch.
