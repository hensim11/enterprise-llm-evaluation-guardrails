# Run Artefact Schema v1

This document defines the machine-readable output of the sequential baseline runner.
A run artefact records raw system execution. It contains no evaluation pass/fail outcome,
score, guardrail decision, retry record, or performance claim.

## Top-level contract

Run artefacts are UTF-8 JSON objects with these exact fields:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact string `"1"`. Unsupported versions are rejected. |
| `run_id` | Non-empty caller-supplied identifier, or a generated UUID. |
| `started_at` | ISO 8601 timestamp normalized to UTC. |
| `system` | System identity plus explicitly supplied non-secret configuration. |
| `dataset` | Dataset source, fingerprint, and ordered validated case snapshot. |
| `results` | One ordered raw execution result for every snapshotted case. |

The writer creates a new file and refuses to overwrite an existing path. The reader
validates required and unknown fields, schema version, case schemas, result invariants,
and dataset fingerprint.

## System provenance

`system.id` identifies the adapter or test double. `system.configuration` is a JSON
object containing its effective, non-secret reproducibility settings. The runner does
not inspect the system object or automatically serialize adapter attributes. Callers
must explicitly allowlist safe configuration values; credentials and secrets must not
be supplied.

## Dataset provenance and fingerprint

`dataset.source` records the path passed to the loader. `dataset.cases` contains the
complete ordered snapshot returned by each validated `EvaluationCase.to_mapping()`.
This retains inputs, context, references, expected behaviour, assertions, tags, risk
category, and metadata for traceability while keeping the system request itself limited
to input and context.

`dataset.fingerprint` has algorithm `sha256`. Its value is SHA-256 over the UTF-8 bytes
of the complete ordered case array encoded as canonical JSON with:

- object keys sorted;
- no insignificant whitespace;
- Unicode preserved rather than ASCII-escaped; and
- non-finite numbers rejected.

The reader recalculates the fingerprint and rejects a mismatch. This detects changes to
the validated snapshot and allows the case specifications used by the run to be
reconstructed. It does not prove source authenticity or guarantee identical future
responses from a model or application.

`DatasetProvenance` defensively copies cases when it is constructed, but retained case
metadata remains mutable under the M1 case contract. The fingerprint is calculated on
demand from the snapshot's current stored values. It therefore validates the snapshot
being serialized or loaded; it is not an immutable identity of execution-time state.
Case IDs must remain unique so every result has one unambiguous provenance record.

## Case execution results

Every result has exactly these fields:

| Field | Success | Error |
| --- | --- | --- |
| `case_id` | ID of the corresponding ordered case | Same |
| `status` | `"success"` | `"error"` |
| `output` | Raw string, including valid `""` | JSON `null` |
| `duration_seconds` | Finite non-negative number | Finite non-negative number |
| `error` | JSON `null` | Object with `type` and `message` strings |

Duration covers the system invocation and response-contract check. It is measured with
Python's monotonic `time.perf_counter()` and recorded in seconds. A successful execution
means only that the system returned a valid `SystemResponse`; it says nothing about
correctness, safety, compliance, or any future evaluation criterion.

An ordinary exception or a return value that is not `SystemResponse` becomes a case
execution error, with the fully qualified exception type and its message retained. The
runner then continues to the next case. It catches `Exception`, not `BaseException`, so
`KeyboardInterrupt`, `SystemExit`, and similar termination signals propagate. Dataset
validation failures, timing failures, artefact serialization failures, and file I/O
failures are run-level errors and are not converted into case results.

## Confidentiality and limitations

Artefacts deliberately contain complete case specifications, raw outputs, and exception
messages. They may therefore be sensitive even though system credentials are excluded.
Review storage and sharing policy, and do not commit generated run artefacts or private
datasets to this repository.

Configuration safety is the caller's responsibility. The runner avoids automatic
adapter introspection, but it does not detect secrets in explicitly supplied
configuration or redact sensitive values from exception messages.

Schema v1 is local and single-process. It does not record evaluators, scores, retries,
concurrency, provider guarantees, code revision, or environment lock data. Those fields
must not be inferred from execution success.
