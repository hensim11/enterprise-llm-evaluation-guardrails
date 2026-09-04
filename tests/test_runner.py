import hashlib
import json
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

import pytest

import llm_eval_guardrails.runner as runner_module
from llm_eval_guardrails import (
    RUN_ARTIFACT_SCHEMA_VERSION,
    CaseExecutionResult,
    DatasetError,
    DatasetProvenance,
    EchoSystemUnderTest,
    EvaluationCase,
    ExecutionStatus,
    RunArtifact,
    SystemRequest,
    SystemResponse,
    load_run_artifact,
    run_dataset,
    write_run_artifact,
)


def case_snapshot_fingerprint(cases: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        cases,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def valid_artifact_mapping() -> dict[str, object]:
    cases = [
        {"schema_version": "1", "id": "one", "input": "first"},
        {"schema_version": "1", "id": "two", "input": "second"},
    ]
    return {
        "schema_version": "1",
        "run_id": "validation-run",
        "started_at": "2026-09-04T12:00:00Z",
        "system": {"id": "test-system", "configuration": {}},
        "dataset": {
            "source": "validation.jsonl",
            "fingerprint": {
                "algorithm": "sha256",
                "value": case_snapshot_fingerprint(cases),
            },
            "cases": cases,
        },
        "results": [
            {
                "case_id": "one",
                "status": "success",
                "output": "first output",
                "duration_seconds": 0.1,
                "error": None,
            },
            {
                "case_id": "two",
                "status": "success",
                "output": "second output",
                "duration_seconds": 0.2,
                "error": None,
            },
        ],
    }


def write_mixed_dataset(path: Path) -> None:
    cases = [
        {
            "schema_version": "1",
            "id": "normal",
            "input": "normal input",
            "context": ["normal context"],
            "references": ["expected reference"],
            "tags": ["reliability"],
            "risk_category": "reliability",
            "expected_behavior": "Return a non-empty response.",
            "assertions": [{"criterion": "example", "type": "contains", "value": "answer"}],
            "metadata": {"owner": "test"},
        },
        {"schema_version": "1", "id": "empty", "input": "empty input"},
        {"schema_version": "1", "id": "exception", "input": "exception input"},
        {"schema_version": "1", "id": "invalid", "input": "invalid input"},
        {
            "schema_version": "1",
            "id": "later",
            "input": "later input",
            "context": ["later context one", "later context two"],
        },
    ]
    path.write_text(
        "".join(json.dumps(case) + "\n" for case in cases),
        encoding="utf-8",
    )


class MixedSystem:
    api_key = "must-not-be-inspected-or-persisted"

    def __init__(self) -> None:
        self.requests: list[SystemRequest] = []

    def invoke(self, request: SystemRequest, /) -> SystemResponse:
        self.requests.append(request)
        if request.input == "normal input":
            return SystemResponse(output="  normal answer  ")
        if request.input == "empty input":
            return SystemResponse(output="")
        if request.input == "exception input":
            raise RuntimeError("ordinary failure")
        if request.input == "invalid input":
            return "not a SystemResponse"  # type: ignore[return-value]
        return SystemResponse(output="later answer")


class NonStringOutputResponse(SystemResponse):
    @property
    def output(self) -> str:
        return 42  # type: ignore[return-value]


class RaisingOutputResponse(SystemResponse):
    @property
    def output(self) -> str:
        raise RuntimeError("output access failed")


def test_mixed_run_is_ordered_isolated_and_contains_only_raw_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_path = tmp_path / "mixed.jsonl"
    write_mixed_dataset(dataset_path)
    system = MixedSystem()
    clock_values = iter([10.0, 10.1, 20.0, 20.2, 30.0, 30.3, 40.0, 40.4, 50.0, 50.5])
    monkeypatch.setattr(runner_module, "perf_counter", lambda: next(clock_values))

    artifact = run_dataset(
        dataset_path,
        system,
        system_id="mixed-test-system",
        system_configuration={"mode": "deterministic"},
        run_id="mixed-run",
        started_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )

    assert [case.id for case in artifact.dataset.cases] == [
        "normal",
        "empty",
        "exception",
        "invalid",
        "later",
    ]
    assert [result.case_id for result in artifact.results] == [
        "normal",
        "empty",
        "exception",
        "invalid",
        "later",
    ]
    assert len(artifact.results) == 5
    assert [result.status for result in artifact.results] == [
        ExecutionStatus.SUCCESS,
        ExecutionStatus.SUCCESS,
        ExecutionStatus.ERROR,
        ExecutionStatus.ERROR,
        ExecutionStatus.SUCCESS,
    ]
    assert [result.output for result in artifact.results] == [
        "  normal answer  ",
        "",
        None,
        None,
        "later answer",
    ]
    assert [result.duration_seconds for result in artifact.results] == pytest.approx(
        [0.1, 0.2, 0.3, 0.4, 0.5]
    )

    exception_error = artifact.results[2].error
    invalid_error = artifact.results[3].error
    assert exception_error is not None
    assert exception_error.type == "builtins.RuntimeError"
    assert exception_error.message == "ordinary failure"
    assert invalid_error is not None
    assert invalid_error.type == "builtins.TypeError"
    assert invalid_error.message == ("system returned builtins.str; expected SystemResponse")

    assert [request.input for request in system.requests] == [
        "normal input",
        "empty input",
        "exception input",
        "invalid input",
        "later input",
    ]
    assert system.requests[-1].context == ("later context one", "later context two")
    assert [item.name for item in fields(SystemRequest)] == ["input", "context"]

    mapping = artifact.to_mapping()
    assert mapping["dataset"]["cases"][0]["references"] == ["expected reference"]
    assert mapping["dataset"]["cases"][0]["expected_behavior"] == ("Return a non-empty response.")
    assert mapping["system"] == {
        "id": "mixed-test-system",
        "configuration": {"mode": "deterministic"},
    }
    assert "api_key" not in json.dumps(mapping)
    assert all(
        set(result) == {"case_id", "status", "output", "duration_seconds", "error"}
        for result in mapping["results"]
    )
    assert "pass" not in {result["status"] for result in mapping["results"]}
    assert "fail" not in {result["status"] for result in mapping["results"]}


@pytest.mark.parametrize(
    ("malformed_response", "expected_type", "expected_message"),
    [
        (
            object.__new__(NonStringOutputResponse),
            "builtins.TypeError",
            "system response output must be a string",
        ),
        (
            object.__new__(RaisingOutputResponse),
            "builtins.RuntimeError",
            "output access failed",
        ),
    ],
)
def test_malformed_response_output_is_isolated_and_next_case_runs(
    tmp_path: Path,
    malformed_response: SystemResponse,
    expected_type: str,
    expected_message: str,
) -> None:
    dataset_path = tmp_path / "two.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"malformed","input":"first"}\n'
        '{"schema_version":"1","id":"later","input":"second"}\n',
        encoding="utf-8",
    )

    class MalformedThenValidSystem:
        calls = 0

        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            self.calls += 1
            if self.calls == 1:
                return malformed_response
            return SystemResponse(output="later output")

    system = MalformedThenValidSystem()
    artifact = run_dataset(dataset_path, system, system_id="malformed-then-valid")

    assert system.calls == 2
    assert [result.status for result in artifact.results] == [
        ExecutionStatus.ERROR,
        ExecutionStatus.SUCCESS,
    ]
    assert [result.output for result in artifact.results] == [None, "later output"]
    assert artifact.results[0].error is not None
    assert artifact.results[0].error.type == expected_type
    assert artifact.results[0].error.message == expected_message


def test_validated_response_output_is_captured_once(tmp_path: Path) -> None:
    dataset_path = tmp_path / "one.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"input"}\n',
        encoding="utf-8",
    )

    class ReadOnceResponse(SystemResponse):
        reads = 0

        @property
        def output(self) -> str:
            type(self).reads += 1
            if type(self).reads > 1:
                raise RuntimeError("output read more than once")
            return "captured output"

    response = object.__new__(ReadOnceResponse)

    class ReadOnceSystem:
        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            return response

    artifact = run_dataset(dataset_path, ReadOnceSystem(), system_id="read-once")

    assert artifact.results[0].status is ExecutionStatus.SUCCESS
    assert artifact.results[0].output == "captured output"
    assert ReadOnceResponse.reads == 1


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt(), SystemExit(2)])
def test_interrupts_propagate(tmp_path: Path, interrupt: BaseException) -> None:
    dataset_path = tmp_path / "one.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"input"}\n',
        encoding="utf-8",
    )

    class InterruptingSystem:
        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            raise interrupt

    with pytest.raises(type(interrupt)):
        run_dataset(dataset_path, InterruptingSystem(), system_id="interrupting")


def test_dataset_validation_failure_is_run_level(tmp_path: Path) -> None:
    dataset_path = tmp_path / "invalid.jsonl"
    dataset_path.write_text('{"schema_version":"1","id":"missing-input"}\n')

    class UncalledSystem:
        called = False

        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            self.called = True
            return SystemResponse(output="unexpected")

    system = UncalledSystem()
    with pytest.raises(DatasetError):
        run_dataset(dataset_path, system, system_id="uncalled")

    assert system.called is False


def test_persisted_artifact_round_trips_with_versioned_provenance(tmp_path: Path) -> None:
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"  exact  ","context":["context"]}\n',
        encoding="utf-8",
    )
    artifact = run_dataset(
        dataset_path,
        EchoSystemUnderTest(),
        system_id="echo",
        system_configuration={"behavior": "input_verbatim", "context_usage": "ignored"},
        run_id="round-trip",
        started_at=datetime(2026, 9, 4, 13, 30, tzinfo=UTC),
    )
    output_path = tmp_path / "run.json"

    write_run_artifact(artifact, output_path)
    loaded = load_run_artifact(output_path)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded.to_mapping() == artifact.to_mapping()
    assert persisted["schema_version"] == RUN_ARTIFACT_SCHEMA_VERSION == "1"
    assert persisted["run_id"] == "round-trip"
    assert persisted["started_at"] == "2026-09-04T13:30:00Z"
    assert persisted["system"]["id"] == "echo"
    assert persisted["dataset"]["source"] == str(dataset_path)
    assert persisted["dataset"]["fingerprint"]["algorithm"] == "sha256"
    assert len(persisted["dataset"]["fingerprint"]["value"]) == 64
    assert persisted["dataset"]["cases"][0]["input"] == "  exact  "
    assert persisted["results"][0]["output"] == "  exact  "
    assert persisted["results"][0]["duration_seconds"] >= 0
    assert persisted["results"][0]["error"] is None


def test_tampered_case_snapshot_fails_fingerprint_validation(tmp_path: Path) -> None:
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"input"}\n',
        encoding="utf-8",
    )
    artifact = run_dataset(dataset_path, EchoSystemUnderTest(), system_id="echo")
    mapping = artifact.to_mapping()
    mapping["dataset"]["cases"][0]["input"] = "tampered"
    output_path = tmp_path / "tampered.json"
    output_path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(ValueError, match="fingerprint does not match"):
        load_run_artifact(output_path)


def test_duplicate_case_ids_are_rejected_by_direct_provenance_construction() -> None:
    first = EvaluationCase(id="duplicate", input="first")
    second = EvaluationCase(id="duplicate", input="second")

    with pytest.raises(
        ValueError,
        match=r"dataset\.cases\[1\]\.id duplicates dataset\.cases\[0\]\.id",
    ):
        DatasetProvenance(source="duplicate.jsonl", cases=(first, second))


def test_duplicate_case_ids_are_rejected_when_matching_fingerprint_is_loaded(
    tmp_path: Path,
) -> None:
    mapping = valid_artifact_mapping()
    cases = mapping["dataset"]["cases"]
    cases[1] = {"schema_version": "1", "id": "one", "input": "second"}
    mapping["results"][1]["case_id"] = "one"
    matching_fingerprint = case_snapshot_fingerprint(cases)
    mapping["dataset"]["fingerprint"]["value"] = matching_fingerprint
    assert matching_fingerprint == case_snapshot_fingerprint(cases)
    output_path = tmp_path / "duplicate.json"
    output_path.write_text(json.dumps(mapping), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"dataset\.cases\[1\]\.id duplicates dataset\.cases\[0\]\.id",
    ):
        load_run_artifact(output_path)


def test_unsupported_artifact_schema_version_is_rejected() -> None:
    mapping = valid_artifact_mapping()
    mapping["schema_version"] = "2"

    with pytest.raises(ValueError, match="unsupported run artefact schema version '2'"):
        RunArtifact.from_mapping(mapping)


@pytest.mark.parametrize(
    ("status", "output", "error", "expected_message"),
    [
        ("success", None, None, "successful result output must be a string"),
        (
            "success",
            "output",
            {"type": "builtins.RuntimeError", "message": "failure"},
            "successful result error must be None",
        ),
        (
            "error",
            "output",
            {"type": "builtins.RuntimeError", "message": "failure"},
            "error result output must be None",
        ),
        ("error", None, None, "error result must include ExecutionError details"),
    ],
)
def test_inconsistent_result_combinations_are_rejected(
    status: str,
    output: object,
    error: dict[str, str] | None,
    expected_message: str,
) -> None:
    mapping = {
        "case_id": "one",
        "status": status,
        "output": output,
        "duration_seconds": 0.1,
        "error": error,
    }

    with pytest.raises(ValueError, match=expected_message):
        CaseExecutionResult.from_mapping(mapping)


@pytest.mark.parametrize("duration", [-1.0, float("nan"), float("inf"), True, "0.1"])
def test_invalid_result_durations_are_rejected(duration: object) -> None:
    mapping = {
        "case_id": "one",
        "status": "success",
        "output": "output",
        "duration_seconds": duration,
        "error": None,
    }

    with pytest.raises((TypeError, ValueError), match="duration_seconds"):
        CaseExecutionResult.from_mapping(mapping)


@pytest.mark.parametrize("result_change", ["missing", "reordered"])
def test_missing_or_reordered_results_are_rejected(result_change: str) -> None:
    mapping = valid_artifact_mapping()
    if result_change == "missing":
        mapping["results"].pop()
    else:
        mapping["results"].reverse()

    with pytest.raises(
        ValueError,
        match="exactly one ordered result for every dataset case",
    ):
        RunArtifact.from_mapping(mapping)


def test_artifact_write_failure_propagates(tmp_path: Path) -> None:
    dataset_path = tmp_path / "cases.jsonl"
    dataset_path.write_text(
        '{"schema_version":"1","id":"one","input":"input"}\n',
        encoding="utf-8",
    )
    artifact = run_dataset(dataset_path, EchoSystemUnderTest(), system_id="echo")
    output_path = tmp_path / "run.json"
    write_run_artifact(artifact, output_path)

    with pytest.raises(FileExistsError):
        write_run_artifact(artifact, output_path)
