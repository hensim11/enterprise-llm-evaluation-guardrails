# Batch C Contract — Calibrated Semantic Evaluation

## Outcome

Measure whether retained Batch B guardrailed responses satisfy their authored semantic
behavioural expectations where literal assertions are insufficient. Raw execution,
deterministic assertions, runtime guardrail decisions, human labels, semantic judgements,
and provider failures remain separate evidence components.

## In scope before the owner-input gate

- rubric, evaluator prompt, output schema, and artefact version 1;
- a synchronous provider-neutral judge interface and ordered full/subset evaluation;
- strict provenance, join, structured-output, evidence-excerpt, and numeric validation;
- one optional OpenAI Responses judge with explicit model and non-secret provenance;
- a fixed, source-ordered, challenge-weighted 12-case calibration subset;
- an exact-evidence human-labelling worksheet containing no inferred labels;
- strict completed-label validation, explicit blinding conditions, and a future worksheet
  that hides deterministic outcomes and selection reasons;
- calibration agreement/confusion reporting and a provenance-bound artefact requiring a
  classification and rationale for every human/judge disagreement;
- combined reporting that keeps execution, deterministic, semantic, human, and runtime
  guardrail fields distinct; and
- offline fake-judge workflow tests and inspected draft artefacts.

## Excluded

No customer-support provider rerun, unauthorized judge call, human-label inference,
runtime guardrail change, semantic enforcement, retries, concurrency, fallback, ensemble,
majority vote, repeated trials, training, fine-tuning, database, service, dashboard,
general policy language, currency-cost calculation, or composite safety/quality score.

## Acceptance evidence

- focused boundary tests and the complete regression suite pass;
- Ruff lint and format checks and `git diff --check` pass;
- the complete 12-case worksheet workflow runs against the exact retained Batch B evidence;
- an offline SDK-shaped fake executes the 12-case semantic workflow and its artefact and
  JSON/Markdown reports reload or regenerate exactly;
- generated artefacts are inspected for correct case order, provenance, draft status,
  component separation, and absence of credentials and machine-specific paths; and
- project documentation and state make the provider-spend and disagreement-review gates
  explicit.

## Validation and stop conditions

The owner supplied all 12 final pass/fail labels and rationales. Preserve them verbatim and
record that they were partially unblinded by the original worksheet. Exercise all other
pre-run workflows without network access and do not inspect `.env`. Stop for separate
authorization of the explicit model and paid 12-call judge run.

After authorization, run only the labelled 12 cases. Classify and rationalize every
disagreement in the validated review artefact and pause for approval if rubric meaning
must change. Run all 36 retained outputs only after the owner accepts calibration evidence.
Batch C and M4 remain incomplete until the authorized real judge evidence is inspected and
accepted.
