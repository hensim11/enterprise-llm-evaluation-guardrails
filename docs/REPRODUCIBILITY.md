# Reproducibility Guide

This guide verifies the package and all reviewed Batch A, B, and C evidence without an API
key or network call to a model provider. Python 3.11 is the minimum supported version; CI
runs the suite on Python 3.11, 3.12, 3.13, and 3.14.

## Fresh clone and normal checks

```bash
git clone https://github.com/hensim11/enterprise-llm-evaluation-guardrails.git
cd enterprise-llm-evaluation-guardrails
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

The core package has no runtime dependencies. The commands above intentionally do not
install the optional OpenAI SDK. Use `.[dev,openai]` only for an explicitly authorized
provider workflow.

## Build and test the installed wheel outside the checkout

This catches missing package files and imports that accidentally depend on the source tree
being the current working directory.

```bash
python -m pip install build
python -m build --wheel
wheel_path="$(find "$PWD/dist" -name 'llm_eval_guardrails-*.whl' -print -quit)"
smoke_dir="$(mktemp -d)"
python -m venv "$smoke_dir/venv"
"$smoke_dir/venv/bin/python" -m pip install "$wheel_path"
(
  cd "$smoke_dir"
  "$smoke_dir/venv/bin/python" -c \
    "import llm_eval_guardrails; print(llm_eval_guardrails.__version__)"
  "$smoke_dir/venv/bin/llm-eval-guardrails" --help
)
```

Expected smoke output includes package version `0.1.0` and CLI usage beginning with
`usage: llm-eval-guardrails`.

## Verify all retained evidence offline

From the repository root, with the project installed:

```bash
python scripts/verify_retained_evidence.py
```

The verifier uses the public strict loaders and canonical aggregation/rendering code. It
loads and joins all retained raw, deterministic, guardrail, comparison, semantic,
human-label, disagreement-review, calibration, and owner-acceptance evidence. It rebuilds
every derivable JSON and Markdown report under a temporary directory, compares generated
bytes with the retained files, and deletes the temporary output. It never modifies
`evidence/`, imports the optional provider adapter, reads credentials, or makes provider
calls.

Expected high-level output is:

```text
Retained evidence verification succeeded (offline; no provider calls).
Batch A baseline: 36 cases; 36/38 literal assertions.
Batch B guardrailed comparison: 35/38 literal assertions; decisions 24 PASS / 3 WARN / 9 BLOCK; 9 invocations avoided.
Batch C calibration: 10/12 exact agreement; 2 reviewed disagreements; owner acceptance valid.
Batch C semantic: 33/36 pass; 3 fail; 36/36 judgement coverage.
```

Any failed schema, provenance, ordering, fingerprint, canonical recomputation, or retained
report comparison produces a non-zero exit. The automated tests also copy the evidence tree,
alter a derived report, and prove that the altered copy is rejected without touching the
retained source.

## What is—and is not—reproduced

The offline command reproduces validation and report generation from already retained
artefacts. It establishes that the stored case snapshots join to the stored results and
that published reports still equal current canonical code. Deterministic assertion results
are recomputed directly from raw outputs.

It does not reproduce the original model responses or semantic-judge responses. Those came
from nondeterministic provider executions, and rerunning them could yield different text or
judgements. Batch B's fresh-provider PASS/WARN differences are therefore observational and
confounded; only the nine input blocks' avoided invocations are directly attributable to
that enforcement path. The 10/12 calibration and 33/36 semantic results are finite retained
observations, not judge-accuracy or general system-performance estimates.

## Credential and data boundaries

- Offline verification requires no `.env`, `OPENAI_API_KEY`, provider SDK, or paid access.
- `.env`, generated `artifacts/`, virtual environments, build output, and credentials are
  ignored by Git.
- Retained evidence contains only fictional benchmark data, including deliberately
  synthetic PIN/card/canary values. It must not be replaced with private customer inputs.
- Raw artefacts preserve full prompts, context, output, configuration allowlists, and
  exception text. The framework does not automatically redact them; review is required
  before retaining any new evidence.
- `store=False` is used by provider workflows, but it does not establish provider-level
  Zero Data Retention or remove ordinary provider handling obligations.

See [the reviewed evidence index](../evidence/README.md),
[the portfolio walkthrough](PORTFOLIO_WALKTHROUGH.md), and
[the artefact specifications](RUN_ARTIFACT_SPEC.md) for deeper inspection.
