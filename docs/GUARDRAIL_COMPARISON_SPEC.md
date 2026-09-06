# Guardrail Comparison Artefact Schema v1

Comparison schema `"1"` joins one baseline raw/evaluated pair to one guardrailed
raw/evaluated/decision set. It refuses comparison unless the dataset fingerprint and
complete ordered case-ID sequence match exactly. Each evaluation artefact and the decision
artefact must first pass its own canonical reconciliation.

## Comparison mode and attribution

`comparison_mode` is explicit machine-readable evidence with one of two values:

- `deterministic_replay`: allowed requests reuse the retained baseline candidate responses;
- `fresh_provider_execution`: allowed requests receive newly sampled provider responses.

The CLI sets `guardrail_comparison_mode` in the guardrailed raw-run configuration from the
selected workflow; it is not a user-supplied comparison label. Canonical comparison checks
derive replay versus fresh execution from the presence of `replay_source_run_id`, require
the declared mode to agree, and require a replay source ID to equal the baseline run ID.

The top-level `attribution` object records separate bases and explanations for input-block
avoidance, PASS/WARN candidate responses, and evaluation deltas. In both modes, an avoided
invocation is directly attributable to an input-stage BLOCK. In deterministic replay, the
same retained candidate responses support attributing differences to guardrail and
deterministic evaluation treatment. In fresh-provider mode, PASS/WARN outputs, outcome
transitions, and metric deltas are observational and potentially confounded by provider or
model nondeterminism; they are not necessarily guardrail-caused. The fresh-provider
Markdown title is explicitly labelled observational.

## Contents

The machine-readable comparison identifies both run IDs and complete system configurations,
its comparison mode and attribution basis, portable evidence references, the guardrail
policy, matched count and ordered case IDs, and every configuration field that differs. It
reports:

- guardrail PASS/WARN/BLOCK counts;
- every detector's version, stage, and trigger count, including zero;
- underlying model invocations avoided by input blocks;
- baseline and guardrailed deterministic assertion and case-outcome counts and deltas;
- baseline-to-guardrailed case-outcome transition counts;
- benign false refusals and benign warnings as separate rates and case-ID lists;
- adversarial block/warn/pass counts;
- count and IDs lacking benign/adversarial classification; and
- a complete ordered case trace with indices, outcomes, decision, trigger identities, and
  invocation/release/replacement flags.

The JSON loader accepts evidence only when the entire stored mapping equals a fresh
canonical recomputation. The Markdown report is rendered from the same mapping and also
supports exact persisted-output validation.

## Portable evidence references

Every evidence link is an object with `base` and `path`. `path` is normalized relative
POSIX text; absolute POSIX paths, absolute Windows paths, and backslash-separated paths are
rejected.

- `comparison_bundle` resolves from the directory containing `comparison.json`. The three
  guardrailed source artefacts use this base. A baseline in a sibling retained bundle may
  also use this base with an explicit `..` segment.
- `repository_root` resolves from the project root. Retained baseline artefacts inside the
  repository use this base and may not contain `..`.

The CLI prefers repository-root references for a baseline retained inside the repository,
then permits a bundle-relative reference only when the baseline is within the comparison
bundle parent's stable subtree. A baseline outside both locations is rejected with an
instruction to copy it into a stable repository or sibling-bundle location. The comparison
never fabricates a misleading relative path for an unrelated external location.

This v1 representation supersedes untracked pre-commit draft comparisons that stored path
strings, including absolute strings. Those drafts are non-canonical and must be regenerated;
there is no retained or released Batch B comparison requiring a schema migration.

## Classification and denominators

A case is benign when it has `benign` or `benign_control`; it is adversarial when it has
`adversarial`. Conflicting labels are rejected. All other cases are explicitly
unclassified.

A **false refusal** is only a guardrail-caused `BLOCK` on a benign-labelled case. Its
denominator is every benign-labelled case. WARN is reported separately and is not a
refusal. Model response wording is never used to infer refusal. Adversarial block/warn/pass
counts are policy observations, not an accuracy score. The comparison does not produce a
composite safety score.

Deterministic deltas retain the literal evaluator's existing meaning and limitations. A
changed assertion outcome does not establish a semantic improvement or regression.
