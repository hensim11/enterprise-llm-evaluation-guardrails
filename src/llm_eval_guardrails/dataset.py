"""UTF-8 JSONL loading for versioned evaluation cases."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

from llm_eval_guardrails.errors import DatasetError, EvaluationCaseValidationError
from llm_eval_guardrails.evaluation_case import EvaluationCase


def load_dataset(path: str | Path) -> list[EvaluationCase]:
    """Load and fully validate an ordered JSONL evaluation dataset.

    Blank and whitespace-only lines are ignored. A file with no applicable records
    is rejected. No cases are returned if any record is invalid.
    """
    dataset_path = Path(path)
    cases: list[EvaluationCase] = []
    first_id_line: dict[str, int] = {}
    record_number = 0

    try:
        with dataset_path.open("r", encoding="utf-8") as dataset_file:
            for line_number, line in enumerate(dataset_file, start=1):
                if not line.strip():
                    continue
                record_number += 1
                raw_case = _parse_json_line(
                    line,
                    dataset_path,
                    line_number=line_number,
                    record_number=record_number,
                )
                case_id = _valid_case_id(raw_case)
                try:
                    case = EvaluationCase.from_mapping(raw_case)
                except EvaluationCaseValidationError as error:
                    raise DatasetError(
                        dataset_path,
                        error.reason,
                        line_number=line_number,
                        record_number=record_number,
                        case_id=case_id,
                        field=error.field,
                    ) from error

                if case.id in first_id_line:
                    raise DatasetError(
                        dataset_path,
                        f"duplicate case identifier {case.id!r} "
                        f"(first seen at line {first_id_line[case.id]})",
                        line_number=line_number,
                        record_number=record_number,
                        case_id=case.id,
                        field="id",
                    )
                first_id_line[case.id] = line_number
                cases.append(case)
    except DatasetError:
        raise
    except UnicodeError as error:
        raise DatasetError(dataset_path, f"unable to decode dataset as UTF-8: {error}") from error
    except OSError as error:
        raise DatasetError(dataset_path, f"unable to read dataset: {error}") from error

    if not cases:
        raise DatasetError(
            dataset_path, "dataset is empty; blank or whitespace-only lines are ignored"
        )
    return cases


def _parse_json_line(line: str, path: Path, *, line_number: int, record_number: int) -> object:
    try:
        return json.loads(
            line,
            object_pairs_hook=_object_from_unique_pairs,
            parse_constant=_reject_non_standard_number,
        )
    except json.JSONDecodeError as error:
        raise DatasetError(
            path,
            f"malformed JSON at column {error.colno}: {error.msg}",
            line_number=line_number,
            record_number=record_number,
        ) from error
    except ValueError as error:
        raise DatasetError(
            path,
            f"malformed JSON: {error}",
            line_number=line_number,
            record_number=record_number,
        ) from error


def _reject_non_standard_number(value: str) -> NoReturn:
    raise ValueError(f"non-standard numeric constant {value!r} is not allowed")


def _object_from_unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r} is not allowed")
        result[key] = value
    return result


def _valid_case_id(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    case_id = value.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        return None
    return case_id
