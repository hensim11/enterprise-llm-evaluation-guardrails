# Enterprise LLM Evaluation & Guardrails

A local-first, provider-agnostic Python framework for versioned LLM evaluation, runtime
guardrail evidence, calibrated semantic judging, and offline verification of retained
results. The reference application is a fictional Northstar Bank support assistant; no
real bank systems, customers, or confidential policies are represented.

> **Release status:** Batches A–D and milestones M0, M1, M2, M4, and M8 are complete.
> M3, M5, M6, and M7 remain in progress. The repository is CV-ready because its bounded
> measurements, architecture, limitations, clean installation path, and interview
> walkthrough are inspectable and reproducible; the broader roadmap is not complete.

## Credential-free quick start

Requires Python 3.11 or newer. The core has no runtime dependencies and this workflow makes
no provider calls.

```bash
git clone https://github.com/hensim11/enterprise-llm-evaluation-guardrails.git
cd enterprise-llm-evaluation-guardrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
python scripts/verify_retained_evidence.py
```

Successful evidence verification ends with:

```text
Batch A baseline: 36 cases; 36/38 literal assertions.
Batch B guardrailed comparison: 35/38 literal assertions; decisions 24 PASS / 3 WARN / 9 BLOCK; 9 invocations avoided.
Batch C calibration: 10/12 exact agreement; 2 reviewed disagreements; owner acceptance valid.
Batch C semantic: 33/36 pass; 3 fail; 36/36 judgement coverage.
```

The verifier loads every retained Batch A–C artefact through strict public APIs,
canonically rebuilds derived JSON and Markdown in temporary storage, byte-compares the
results, and fails non-zero on drift. See the copy-pasteable
[reproducibility guide](docs/REPRODUCIBILITY.md) for wheel installation and an installed-CLI
smoke test from outside the checkout.

## Measured results

| Batch | Retained observation | Interpretation boundary |
| --- | --- | --- |
| A — baseline | 36/38 literal assertions passed; 36/36 executions completed | Narrow, case-sensitive assertion result—not general accuracy, correctness, or safety |
| B — runtime guardrails | 35/38 literal assertions passed; 24 PASS, 3 WARN, 9 BLOCK; nine input blocks avoided invocation | Avoidance is directly attributable; fresh-provider output and metric differences are observational and confounded |
| C — calibration | 10/12 exact human/judge agreement with two reviewed disagreements | Challenge-weighted, partially-unblinded diagnostic—not judge accuracy or system performance |
| C — full semantic | 33/36 pass, three fail, 36/36 judgement coverage | One LLM-judged finite benchmark observation—not general accuracy, safety, security, or judge accuracy |

The three semantic failures were BLOCK replacement responses that omitted required
boundaries or helpful action. That result demonstrates why enforcement action and measured
response quality must remain separate. Follow every aggregate into the
[reviewed evidence index](evidence/README.md), or use the
[portfolio walkthrough](docs/PORTFOLIO_WALKTHROUGH.md) for a six-case reviewer trail,
trade-offs, a short demo, and interview/CV wording.

## Implemented architecture

```text
versioned cases
      |
      v
request guardrails --BLOCK--> replacement output + guardrail decision
      |
   PASS/WARN
      v
system under test --> candidate --> response guardrails --> released/replaced raw output
                                               |
                                               +--> separate guardrail decision evidence

retained raw output + assertions --> deterministic evidence --> JSON/Markdown report
retained raw output + rubric -----> semantic evidence -------> combined report
12 retained outputs + owner labels --> calibration + review + owner acceptance
```

Runtime guardrails act only at the request/candidate-response boundary. Offline evaluation
reports do not produce runtime guardrail decisions. Raw execution status, deterministic
outcomes, semantic judgements, human labels, policy decisions, and governance acceptance
remain distinct and are joined by versioned provenance.

Implemented capability includes:

- strict, typed schema-v1 JSONL cases and a 36-case fictional benchmark;
- a synchronous `SystemUnderTest` protocol, sequential runner, per-case error isolation,
  complete case snapshots, and SHA-256 dataset fingerprints;
- literal `exact_match`, `contains`, and `not_contains` evaluation with pass, fail, error,
  and not-applicable outcomes;
- reconciled aggregation and shared canonical JSON/Markdown rendering;
- narrow versioned input/response guardrails with `BLOCK > WARN > PASS` precedence,
  invocation/release evidence, and matched comparison reports;
- a versioned binary semantic rubric, provider-neutral judge contract, optional OpenAI
  adapter, strict output validation, token-usage evidence, and component-separated reports;
- challenge-weighted human calibration with disclosed blinding, exact agreement/confusion
  counts, exhaustive disagreement review, and provenance-bound owner acceptance; and
- a credential-free retained-evidence verifier plus Python 3.11–3.14 CI, wheel build, clean
  install, and outside-checkout CLI smoke verification.

The core package declares no dependencies. The official OpenAI SDK is isolated behind the
optional `openai` extra and is needed only for explicitly authorized provider runs.

## How evidence moves through the system

1. The runner gives the system only input text and ordered context. Case identity,
   expectations, assertions, risk labels, and metadata stay in the evaluation layer.
2. A raw-run artefact records the complete validated case snapshot, system/configuration
   provenance, ordered outputs, durations, and explicit execution errors.
3. Deterministic evaluation is canonically recomputed from the raw output. A separate
   artefact and strict join prevent evaluation status from being confused with execution.
4. Runtime guardrails create separate per-case decision evidence. Comparisons require the
   same fingerprint and ordered case IDs and record whether candidates were replayed or
   freshly generated.
5. Semantic judging consumes retained outputs and authored behaviour, not new system
   executions. Calibration and full measurement are retained separately.
6. Machine and human reports share one aggregate representation, preserving denominators,
   missing/error outcomes, component counts, and case-level traceability.

## Run the implemented offline workflows

Create a synthetic plumbing run (not model-quality evidence):

```bash
python -m llm_eval_guardrails run-echo \
  examples/evaluation_cases.jsonl \
  /tmp/synthetic-echo-run.json \
  --run-id synthetic-echo-demo
```

Evaluate an existing raw run into a new atomic bundle:

```bash
python -m llm_eval_guardrails evaluate \
  /path/to/raw-run.json \
  /path/to/new-evaluation-bundle
```

Prepare a future blinded human-calibration worksheet without a provider call:

```bash
python -m llm_eval_guardrails prepare-semantic-calibration \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  /path/to/new-calibration-worksheet \
  --blinded
```

Provider-backed commands are documented but require separate credential/spend
authorization. Install them with `python -m pip install -e ".[dev,openai]"`; never put a
credential in a CLI argument or retained artefact.

## Documentation and repository map

| Path | Purpose |
| --- | --- |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Clean clone, checks, wheel install, CLI smoke, and offline evidence verification |
| [`docs/PORTFOLIO_WALKTHROUGH.md`](docs/PORTFOLIO_WALKTHROUGH.md) | Architecture, case trail, findings, trade-offs, limitations, and interview wording |
| [`docs/BATCH_D_CONTRACT.md`](docs/BATCH_D_CONTRACT.md) | Release scope, exclusions, acceptance evidence, and stop conditions |
| [`docs/DELIVERY_WORKFLOW.md`](docs/DELIVERY_WORKFLOW.md) | Batch boundaries, review gates, and completion evidence |
| [`docs/EVALUATION_SPEC.md`](docs/EVALUATION_SPEC.md) | Evaluation dimensions, outcome taxonomy, aggregation, and methodology |
| [`docs/RUN_ARTIFACT_SPEC.md`](docs/RUN_ARTIFACT_SPEC.md) | Raw run schema, provenance, fingerprint, errors, and confidentiality |
| [`docs/EVALUATION_ARTIFACT_SPEC.md`](docs/EVALUATION_ARTIFACT_SPEC.md) | Deterministic evidence joins, outcomes, and denominators |
| [`docs/GUARDRAIL_POLICY.md`](docs/GUARDRAIL_POLICY.md) | Implemented Northstar policy boundary, detectors, precedence, and limits |
| [`docs/GUARDRAIL_ARTIFACT_SPEC.md`](docs/GUARDRAIL_ARTIFACT_SPEC.md) | Runtime decision evidence and reconciliation |
| [`docs/GUARDRAIL_COMPARISON_SPEC.md`](docs/GUARDRAIL_COMPARISON_SPEC.md) | Matched-run modes, attribution, paths, and classification |
| [`docs/SEMANTIC_RUBRIC.md`](docs/SEMANTIC_RUBRIC.md) | Binary authored-behaviour rubric and trust boundary |
| [`docs/SEMANTIC_ARTIFACT_SPEC.md`](docs/SEMANTIC_ARTIFACT_SPEC.md) | Semantic provenance, validation, failures, usage, and reporting |
| [`evidence/README.md`](evidence/README.md) | Reviewed empirical bundles, metrics, provenance, and limitations |
| [`DECISIONS.md`](DECISIONS.md) | Architectural and methodological decision records |
| [`ROADMAP.md`](ROADMAP.md) / [`PROJECT_STATE.md`](PROJECT_STATE.md) | Honest milestone status and verified current state |

Source lives in `src/llm_eval_guardrails/`, tests in `tests/`, versioned cases in
`benchmarks/`, illustrative non-evidence data in `examples/`, and deliberately retained
reviewed evidence in `evidence/`.

## Important limitations

- The retained evidence covers one small fictional benchmark and finite provider runs; it
  does not establish production quality, compliance, security, privacy, or robustness.
- Literal checks are exact surface comparisons. Five cases have no deterministic assertion;
  semantic coverage does not make the LLM judge ground truth.
- Guardrail v1 is a narrow phrase/regex/digit-shape policy, not semantic understanding,
  broad PII detection, redaction, or a general threshold engine. It can miss attacks or
  produce false positives.
- The two Batch A/B provider runs do not retain token usage. The Batch C judge run does, but
  the repository does not infer currency cost.
- The runner is sequential and has no retry, resume, or concurrency support. Judge
  variance, prompt sensitivity, threshold sensitivity, and broader compatibility hardening
  remain M7 work.
- Raw artefacts may contain complete inputs, context, outputs, configuration allowlists,
  and exceptions. The framework does not automatically redact sensitive data.
- Fingerprints detect stored snapshot drift; they do not prove authenticity or reproduce
  nondeterministic provider responses.
- The completed 12-case labels were partially unblinded. One case received different
  calibration/full-run judge outcomes; this demonstrates possible variance but does not
  quantify it.

For the detailed risk register and next objective, see
[`PROJECT_STATE.md`](PROJECT_STATE.md). The next recommended batch is bounded M7 hardening:
measure judge variance and prompt sensitivity before choosing thresholds, then add tested
resume/failure behaviour and compatibility checks.
