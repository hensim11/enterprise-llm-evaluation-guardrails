# Semantic Calibration Workflow

## Completed owner-label gate

The fixed Batch C subset contains all five Batch B deterministic `not_applicable` cases,
all three deterministic failures, and four additional stratified cases. It is deliberately
challenge-weighted, not representative, and not an estimator of overall system or judge
performance. Human labels are calibration references, not universal truth.

The owner completed all 12 judgements: 8 `pass` and 4 `fail`. The strict artefact is
`evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json`.
These are final owner judgements and must not be inferred, normalized, or rewritten.

These labels are recorded as **partially unblinded**. The original worksheet exposed both
the deterministic outcomes and the reasons cases were selected. That disclosure limits
how strongly agreement can be interpreted, but it does not invalidate or alter the
completed labels. Future calibration exercises should generate the blinded worksheet,
which retains the case evidence required for judgement while omitting those two fields:

```bash
.venv/bin/python -m llm_eval_guardrails prepare-semantic-calibration \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  artifacts/future-blinded-calibration-worksheet \
  --blinded
```

Completed labels use semantic rubric version `1`. The loader requires `status=complete`,
the exact run ID and fingerprint, the fixed case IDs and raw indices exactly once in
source order, valid pass/fail labels, non-empty rationales, and explicit labelling
conditions:

```json
{
  "schema_version": "1",
  "status": "complete",
  "rubric": {"id": "authored-expected-behaviour", "version": "1"},
  "source_run": {
    "run_id": "EXACT_WORKSHEET_RUN_ID",
    "dataset_fingerprint": "EXACT_WORKSHEET_FINGERPRINT"
  },
  "labelling_conditions": {
    "blinding": "partially_unblinded",
    "disclosures": [
      "worksheet_exposed_deterministic_outcomes",
      "worksheet_exposed_selection_reasons"
    ]
  },
  "labels": [
    {
      "case_id": "EXACT_SELECTED_CASE_ID",
      "raw_result_index": 5,
      "label": "pass",
      "rationale": "Owner-authored rationale preserved verbatim."
    }
  ]
}
```

Validate the completed retained labels offline before any judge run:

```bash
.venv/bin/python -m llm_eval_guardrails validate-human-labels \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json
```

## Completed authorized 12-call judge gate

The separately authorized replacement run judged the same 12 retained outputs without
rerunning the customer-support model. Its exact command was:

```bash
.venv/bin/python -m llm_eval_guardrails run-openai-semantic \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  artifacts/northstar-v1-guardrailed-batch-c-calibration-judge-rerun \
  --model gpt-5.5-2026-04-23 \
  --max-output-tokens 2000 \
  --calibration-subset \
  --human-labels evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json \
  --guardrail-decisions evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/guardrail-decisions.json
```

Do not repeat this historical paid command without fresh explicit authorization.

The command makes one application-level call per selected successful case with authored
expected behaviour: exactly 12 for this retained set. It has no application or SDK
retries, fallback, or concurrency, and every request sets `store=false`.
The OpenAI transmitted output-schema provenance is version `2`; uniqueness of response
excerpts and failure modes is enforced by local provider-neutral validation rather than by
unsupported provider-schema keywords. A provider rejection that identifies a run-wide
structured-output configuration defect aborts immediately after the first attempted case.
Ordinary case-specific judge failures remain isolated.

It atomically writes `semantic-evaluation.json`, `semantic-summary.json`, and
`semantic-report.md`. The combined report carries the completed human labels and their
partially-unblinded conditions alongside separate raw, deterministic, semantic, and
guardrail components.

Provider usage is retained only when a call returns a structurally valid completed
pass/fail judgement with usage. If a provider call consumed tokens but then failed, or its
response was incomplete or malformed, the resulting judge-error row has `usage=null` and
that call's usage may be discarded. Therefore usage totals can be incomplete when judge
errors exist; the workflow never infers currency cost.

### Preserved failed attempt

The first authorized attempt on 2026-09-07 used `gpt-5.5-2026-04-23`, a 2,000-token output
cap, and no application or SDK retries. All 12 requests were rejected with HTTP 400 because
provider-schema version `1` transmitted unsupported `uniqueItems` keywords. It produced 0
valid pass/fail judgements, 12 judge errors, 0/12 judgement coverage, and undefined exact
agreement. Every usage field is `null`; usage and billing are therefore unknown, not zero.

The failed semantic bundle remains unchanged under
`artifacts/northstar-v1-guardrailed-batch-c-calibration-judge/`, with its initial report and
empty incomplete disagreement draft under
`artifacts/northstar-v1-guardrailed-batch-c-calibration-report/`. The empty draft is not
completed disagreement evidence and must not be classified as such. The schema remediation
does not authorize a replacement run: a fresh explicit model and paid-call authorization
is required, and the rerun must use new output directories.

## Calibration report and disagreement gate

First reconcile the completed labels and semantic evidence without a review artefact:

```bash
.venv/bin/python -m llm_eval_guardrails report-semantic-calibration \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  artifacts/northstar-v1-guardrailed-batch-c-calibration-judge-rerun/semantic-evaluation.json \
  evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json \
  artifacts/northstar-v1-guardrailed-batch-c-calibration-rerun-report
```

This writes `calibration.json`, `calibration.md`, and fillable
`disagreement-review.draft.json`/`.md`. Copy the draft JSON to
`disagreement-review.completed.json`; then set its status to `complete` and provide exactly
one classification and a non-empty owner review rationale for every row. Each row already
contains its case ID, raw index, human label, and judge outcome. Allowed classifications
are `rubric_ambiguity`, `human_label_ambiguity`, `judge_failure`, and
`implementation_defect`.

The completed disagreement artefact is cryptographically bound to the canonical semantic
and human-label artefacts and to their run, fingerprint, rubric, and judge. The loader
rejects drafts, stale hashes, duplicates, omissions, extra or reordered cases, altered
human/judge outcomes, invalid classifications, and blank rationales.

Regenerate the calibration report with the completed review:

```bash
.venv/bin/python -m llm_eval_guardrails report-semantic-calibration \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  artifacts/northstar-v1-guardrailed-batch-c-calibration-judge-rerun/semantic-evaluation.json \
  evidence/calibration/northstar-v1-guardrailed-batch-c-draft/human-labels.completed.json \
  artifacts/northstar-v1-guardrailed-batch-c-calibration-rerun-reviewed \
  --disagreement-review artifacts/northstar-v1-guardrailed-batch-c-calibration-rerun-report/disagreement-review.completed.json
```

Calibration reports exact agreement, disagreement and judge-error counts, judgement
coverage, all four binary human/judge confusion counts, and case-level rationales and
evidence. Eligibility for owner acceptance requires both of these independent gates:

1. Every selected case has a completed `pass` or `fail` judge result, giving full judgement
   coverage and zero judge errors.
2. If disagreements exist, every disagreement has a classification and rationale in the
   validated, completed provenance-bound review artefact.

Completing disagreement reviews cannot compensate for a judge error or partial coverage.
Likewise, full coverage cannot compensate for an unresolved disagreement. The computed
report never marks `owner_accepted=true`; acceptance remains an explicit external owner
decision. A material rubric change requires owner approval and a new rubric version.

For this run, all 12 judgements completed with zero judge errors and 10/12 exact agreement.
The owner reviewed both disagreements, retaining `judge_failure` for
`support-travel-notice-guidance` and `human_label_ambiguity` for
`unsupported-fraud-refund-guarantee`, then accepted the calibration on 2026-09-07.
The separate schema-v1 `owner-acceptance.json` binds that decision to canonical hashes of
the exact reviewed calibration report and completed disagreement review, records the
observed 10/12 result, and acknowledges the challenge-weighted, non-representative,
partially-unblinded, non-ground-truth limitations. The accepted six-file package is retained
under
`evidence/calibration/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907/`.
This closed the calibration gate but did not itself authorize the full 36-case semantic
measurement.

## Subsequent full semantic measurement

After separate explicit authorization, the accepted configuration was applied once to all
36 retained Batch B outputs. The run made no customer-support system calls and produced 36
completed semantic judgements: 33 pass, 3 fail, 0 error, 0 N/A, and 100% judgement
coverage. Complete retained usage was 16,266 input, 5,068 output, and 21,334 total tokens.
The reviewed three-file bundle is retained under
`evidence/semantic/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907/`.

The exact historical command was:

```bash
.venv/bin/python -m llm_eval_guardrails run-openai-semantic \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/raw-run.json \
  evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/evaluated-run.json \
  artifacts/northstar-v1-guardrailed-batch-c-semantic-full-gpt-5.5-2026-04-23-20260907 \
  --model gpt-5.5-2026-04-23 \
  --max-output-tokens 2000 \
  --guardrail-decisions evidence/guardrails/northstar-v1-gpt-5.4-mini-2026-03-17-guardrailed-20260906/guardrail-decisions.json \
  --human-labels evidence/calibration/northstar-v1-guardrailed-batch-c-gpt-5.5-2026-04-23-20260907/human-labels.completed.json
```

Do not repeat this paid command without separate explicit authorization.

All three semantic failures were guardrail BLOCK replacement responses classified with
`omitted_required_boundary_or_helpful_action`. Nine BLOCK decisions reconciled to six
semantic passes and three failures; every PASS (24) and WARN (3) decision semantically
passed. Deterministic outcomes reconciled to 28 pass→pass, two fail→pass, one fail→fail,
three N/A→pass, and two N/A→fail.

`support-travel-notice-guidance` changed from judge fail during calibration to judge pass
in the full measurement. This does not change the immutable accepted calibration or its
10/12 agreement. It is a single observed repeat showing that the judge can vary, not a
recalibration or an estimate of judge variance.

## Limitations and threats

- Partial unblinding can influence the completed human labels and limits agreement claims.
- Prompt injection can target the judge; treating inputs as untrusted evidence is not a
  security guarantee.
- A judge can share training, model-family, or provider biases with the system under test.
- One full-run judgement per case and one observed repeat on the calibration overlap do not
  estimate repeat-trial variance.
- Results are sensitive to rubric wording, prompt formatting, model snapshot, and provider
  behaviour.
- Twelve challenge-weighted labels support disagreement inspection, not precise judge
  accuracy or overall performance estimates.
- Provider token counts can be incomplete around errors and do not establish currency cost.
