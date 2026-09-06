# Repository working agreement

This repository is the source of truth. Before meaningful work, read `PROJECT_VISION.md`, `ROADMAP.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `README.md`, and `docs/DELIVERY_WORKFLOW.md`.

- Keep evaluation measurement distinct from guardrail enforcement.
- Treat one bounded, demonstrable capability batch as the unit of owner review. Within a
  batch, implement through narrow, independently verifiable increments and continue
  without asking the owner to orchestrate routine implementation details.
- Define the batch objective, exclusions, acceptance evidence, and stop conditions before
  coding. Prefer one branch and one review cycle per batch.
- Pause only for a decision that materially changes architecture, evaluation methodology,
  cost/credentials, or agreed scope, or for a blocker that cannot be resolved safely from
  repository evidence. Diagnose and fix ordinary test, lint, fixture, and implementation
  failures autonomously.
- Finish each batch with a runnable path, proportionate tests, inspected artefacts or
  outputs, and an evidence-based completion report.
- Do not describe planned functionality as implemented.
- Never fabricate evaluation results or security claims.
- Prefer simple, typed Python interfaces and local artefacts until complexity is justified.
- Add or update tests with behavioural changes.
- Update `PROJECT_STATE.md` after meaningful implementation work.
- Update `DECISIONS.md` only for meaningful architectural or methodological decisions.
- Do not commit credentials or private inputs. Generated run artefacts stay untracked by
  default; publish only deliberately selected, reviewed, non-sensitive evidence artefacts.
