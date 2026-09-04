"""Sequential raw execution of validated evaluation datasets."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from llm_eval_guardrails.dataset import load_dataset
from llm_eval_guardrails.run_artifact import (
    CaseExecutionResult,
    DatasetProvenance,
    ExecutionError,
    ExecutionStatus,
    JsonValue,
    RunArtifact,
    SystemProvenance,
)
from llm_eval_guardrails.system_under_test import (
    SystemRequest,
    SystemResponse,
    SystemUnderTest,
)


def run_dataset(
    dataset_path: str | Path,
    system: SystemUnderTest,
    *,
    system_id: str,
    system_configuration: Mapping[str, JsonValue] | None = None,
    run_id: str | None = None,
    started_at: datetime | None = None,
) -> RunArtifact:
    """Run every validated case sequentially and return raw execution evidence.

    ``system_configuration`` is an explicit non-secret allowlist for provenance. The
    runner never inspects the system object, so adapter credentials are not persisted.
    Dataset validation and unexpected run-level failures propagate to the caller.
    """
    cases = load_dataset(dataset_path)
    dataset = DatasetProvenance(source=str(dataset_path), cases=tuple(cases))
    system_provenance = SystemProvenance(
        id=system_id,
        configuration={} if system_configuration is None else system_configuration,
    )
    actual_run_id = str(uuid4()) if run_id is None else run_id
    actual_started_at = datetime.now(UTC) if started_at is None else started_at
    if not isinstance(actual_run_id, str):
        raise TypeError("run_id must be a string")
    if not actual_run_id.strip():
        raise ValueError("run_id must be a non-empty string")
    if not isinstance(actual_started_at, datetime):
        raise TypeError("started_at must be a datetime")
    if actual_started_at.tzinfo is None or actual_started_at.utcoffset() is None:
        raise ValueError("started_at must include a timezone")

    results: list[CaseExecutionResult] = []
    for case in cases:
        request = SystemRequest(input=case.input, context=case.context)
        start = perf_counter()
        try:
            response = system.invoke(request)
            if not isinstance(response, SystemResponse):
                raise TypeError(
                    "system returned "
                    f"{type(response).__module__}.{type(response).__qualname__}; "
                    "expected SystemResponse"
                )
            output = response.output
            if not isinstance(output, str):
                raise TypeError("system response output must be a string")
        except Exception as error:
            duration = perf_counter() - start
            results.append(
                CaseExecutionResult(
                    case_id=case.id,
                    status=ExecutionStatus.ERROR,
                    output=None,
                    duration_seconds=duration,
                    error=ExecutionError(
                        type=f"{type(error).__module__}.{type(error).__qualname__}",
                        message=str(error),
                    ),
                )
            )
        else:
            duration = perf_counter() - start
            results.append(
                CaseExecutionResult(
                    case_id=case.id,
                    status=ExecutionStatus.SUCCESS,
                    output=output,
                    duration_seconds=duration,
                    error=None,
                )
            )

    return RunArtifact(
        run_id=actual_run_id,
        started_at=actual_started_at,
        system=system_provenance,
        dataset=dataset,
        results=tuple(results),
    )
