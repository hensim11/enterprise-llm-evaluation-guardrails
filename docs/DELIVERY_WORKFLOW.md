# Delivery Workflow

Last updated: 2026-09-05

## Objective

Reach a technically defensible, GitHub-ready and CV-ready version quickly. Optimise for
working vertical capabilities, retained evidence, real measurements, and decisions the
project owner can explain. Do not optimise for completing every roadmap subsection in a
separate conversation.

The target first release lets a reviewer run a versioned fictional-bank benchmark against
a real system, inspect case-level evidence, compare baseline and guardrailed behaviour,
and understand the limits of the measurements.

## Unit of delivery

The owner-facing unit of work is a **bounded capability batch**. A batch should end in a
meaningful outcome that can be run, measured, demonstrated, or discussed.

Incremental engineering still happens inside the batch. Codex should implement a batch as
small verified steps, such as contract, tests, implementation, integration, artefact,
command-line path, and end-to-end validation. Routine failures are handled inside the same
implementation session instead of becoming separate owner review cycles.

Default to one branch, one pull request, and one strategic review per batch. Split a batch
only when repository evidence reveals a material architectural or methodological decision,
an external dependency such as credentials or spend blocks the acceptance evidence, or the
original scope is no longer coherent.

## Batch cycle

1. **Inspect current evidence.** Read the core project documents, working tree, relevant
   implementation, tests, and recent diffs. Planned work is never treated as implemented.
2. **Set a batch contract.** State one capability outcome, in-scope work, explicit
   exclusions, acceptance criteria, validation, and any user-owned dependency.
3. **Build autonomously.** Work through narrow internal increments. Fix ordinary code,
   test, lint, fixture, and documentation issues without returning control to the owner.
4. **Produce evidence.** Run the relevant command or experiment, inspect the generated
   artefact, run proportionate tests and checks, and record exact commands and outcomes.
5. **Review once.** Audit the whole batch against repository evidence and classify findings
   using the review gate below. Fix material issues; avoid reopening the batch for optional
   polish.
6. **Learn and commit.** Explain the data flow, decisions, limitations, and interview story.
   Update project state accurately, commit the accepted batch, and select the next batch.

## When owner input is required

Return to the owner during a batch only when:

- a choice changes architecture, evaluation validity, or the interpretation of metrics;
- credentials, paid model execution, or another external action is needed;
- a discovered constraint would materially expand or invalidate the agreed batch; or
- a blocker remains after safe, in-scope diagnosis and alternatives have been exhausted.

Do not stop for routine implementation choices already governed by the repository,
repairable test or lint failures, fixture updates, additional boundary tests, or minor
refactors required to complete the agreed capability.

## Batch completion evidence

A batch is complete only when all applicable items are true:

- the capability works through a documented runnable entry point;
- acceptance criteria are demonstrated by inspected output, not only mocked unit tests;
- important behaviour and failure paths have proportionate automated tests;
- relevant lint, format, and test checks pass once after the final change;
- artefact schemas, denominators, errors, and missing outcomes remain explicit;
- `PROJECT_STATE.md` matches repository reality;
- `DECISIONS.md` changes only for a meaningful architectural or methodological decision;
- limitations and unresolved issues are recorded without inflating claims; and
- the completion report lists changes, evidence, decisions, unresolved risks, and the
  recommended next capability batch.

Real-model experiment batches are not complete until a real run has been executed and its
outputs inspected. If credentials or spend are unavailable, implementation may be ready,
but the batch remains blocked on empirical evidence rather than being reported as measured.

## Strategic review gate

Every review must place each finding in one of four categories:

- **BLOCKER:** incorrect or misleading results, invalid methodology, broken reproducibility,
  unsafe handling of secrets/data, or a major missing acceptance criterion.
- **FIX BEFORE COMMIT:** a bounded weakness that materially affects correctness,
  credibility, or the promised workflow.
- **HARDEN LATER:** a worthwhile improvement that does not prevent a credible batch.
- **IGNORE FOR NOW:** an imperfection whose cost exceeds its current value.

The review ends with an explicit decision: **commit and move on**, **fix before commit**, or
**re-scope because blocked**.

## Fast-track batches from the completed M2 boundary

These batches are delivery units, not replacements for milestone status. They intentionally
cross roadmap milestones to produce useful vertical slices sooner.

### Batch A — First measured baseline

Outcome: run a small, high-quality, versioned fictional-bank benchmark against one real
provider-backed system and produce traceable baseline metrics.

In scope:

- execute the existing exact-match, contains, and not-contains assertions with explicit
  pass, fail, error, and not-applicable semantics;
- preserve evaluator evidence separately from raw execution status;
- add the minimum aggregation and machine-readable/human-readable reporting needed for
  totals, denominators, per-category results, errors, and case-level traceability;
- add one real provider adapter behind the existing provider-neutral interface;
- create an initial benchmark of roughly 30–40 deliberately designed cases spanning normal
  support, grounded policy questions, hallucination traps, refusal boundaries, sensitive
  data, injection attempts, and benign controls;
- expose one documented end-to-end command and run a real baseline experiment; and
- retain a reviewed, non-sensitive evidence set suitable for supporting published claims.

Excluded: guardrail enforcement, model-based judging, concurrency, retries, dashboards,
and additional providers.

Acceptance evidence: a real retained run, evaluated case records, a report whose metrics
reconcile to case evidence, passing relevant checks, and honest limitations about benchmark
size and evaluator coverage.

### Batch B — Guardrail impact comparison

Outcome: apply a small set of explicit runtime guardrails and compare the baseline and
guardrailed system on the same benchmark.

In scope: input and response detectors justified by the cases, separate pass/warn/block
policy decisions, adversarial and benign-control coverage, matched-run comparison, false
refusal measurement, and case-linked reporting.

Excluded: claims of security guarantees, a general policy language, hosted enforcement,
and broad detector catalogues.

### Batch C — Semantic evaluation and calibration

Outcome: measure important behaviours that deterministic assertions cannot assess reliably.

In scope: a versioned structured rubric, validated judge outputs, explicit judge errors, a
small human-labelled calibration subset, agreement/disagreement analysis, and integration
into the existing reports without hiding component outcomes.

Excluded: training or fine-tuning an evaluator, large-scale annotation, and treating the
judge as ground truth.

### Batch D — Reproducibility and portfolio release

Outcome: make the measured system easy to clone, run, inspect, and explain.

In scope: clean-environment verification, supported-Python confirmation, final methodology
and limitations, architecture and data-flow documentation, curated example evidence,
results analysis, and truthful GitHub/CV wording.

Optional sophistication starts only after this release or when evidence exposes a concrete
need.
