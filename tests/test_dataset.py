import json
from pathlib import Path

import pytest

from llm_eval_guardrails import (
    DatasetError,
    EvaluationCase,
    EvaluationCaseValidationError,
    load_dataset,
)

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]


def serialized_case(case_id: str, text: str = "Hello") -> dict[str, object]:
    return {"schema_version": "1", "id": case_id, "input": text}


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def test_multiple_records_load_in_source_order_with_unicode(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    write_jsonl(
        path,
        [
            serialized_case("first", "こんにちは"),
            serialized_case("second", "Zażółć gęślą jaźń"),
            serialized_case("third", "مرحبا"),
        ],
    )

    cases = load_dataset(path)

    assert [case.id for case in cases] == ["first", "second", "third"]
    assert [case.input for case in cases] == ["こんにちは", "Zażółć gęślą jaźń", "مرحبا"]


def test_representative_valid_fixture_loads() -> None:
    cases = load_dataset(FIXTURES / "valid_cases.jsonl")

    assert [case.id for case in cases] == ["minimal", "grounded-answer"]


def test_documented_example_dataset_loads_through_public_api() -> None:
    cases = load_dataset(ROOT / "examples" / "evaluation_cases.jsonl")

    assert [case.id for case in cases] == ["support-refund-policy", "privacy-canary"]


def test_representative_invalid_fixture_fails_at_missing_field() -> None:
    path = FIXTURES / "invalid_missing_input.jsonl"

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value) == (
        f"{path}: line 1, record 1, case 'missing-input': field 'input': is required"
    )


def test_blank_lines_are_ignored_and_physical_line_numbers_are_preserved(tmp_path: Path) -> None:
    path = tmp_path / "blank-lines.jsonl"
    path.write_text(
        '\n  \t\n{"schema_version":"1","id":"one","input":"First"}\n\n'
        '{"schema_version":"1","id":"two","input":"Second"}\n',
        encoding="utf-8",
    )

    cases = load_dataset(path)

    assert [case.id for case in cases] == ["one", "two"]


@pytest.mark.parametrize("content", ["", "\n \n\t\n"])
def test_empty_or_blank_only_dataset_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value) == (
        f"{path}: dataset is empty; blank or whitespace-only lines are ignored"
    )
    assert caught.value.line_number is None


@pytest.mark.parametrize(
    ("bad_index", "expected_line", "expected_record"),
    [(0, 1, 1), (1, 2, 2), (2, 3, 3)],
)
def test_malformed_json_reports_first_middle_and_final_record_locations(
    tmp_path: Path, bad_index: int, expected_line: int, expected_record: int
) -> None:
    path = tmp_path / "malformed.jsonl"
    lines = [json.dumps(serialized_case(f"case-{index}")) for index in range(3)]
    lines[bad_index] = '{"schema_version":"1","id":}'
    path.write_text("\n".join(lines), encoding="utf-8")

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert caught.value.line_number == expected_line
    assert caught.value.record_number == expected_record
    assert "malformed JSON at column" in caught.value.reason
    assert str(caught.value).startswith(
        f"{path}: line {expected_line}, record {expected_record}: malformed JSON"
    )
    assert isinstance(caught.value.__cause__, json.JSONDecodeError)


def test_schema_error_reports_file_line_record_and_field(tmp_path: Path) -> None:
    path = tmp_path / "invalid.jsonl"
    path.write_text(
        '\n{"schema_version":"1","id":"valid","input":"First"}\n'
        '{"schema_version":"1","id":"invalid","input":42}\n',
        encoding="utf-8",
    )

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value) == (
        f"{path}: line 3, record 2, case 'invalid': field 'input': must be a string"
    )
    assert caught.value.field == "input"
    assert caught.value.line_number == 3
    assert caught.value.record_number == 2
    assert caught.value.case_id == "invalid"


@pytest.mark.parametrize(
    ("invalid_field", "invalid_value", "expected_field"),
    [
        ("references", [1], "references[0]"),
        ("risk_category", None, "risk_category"),
        ("expected_behavior", None, "expected_behavior"),
    ],
)
def test_direct_and_loader_validation_report_same_field_and_reason(
    tmp_path: Path,
    invalid_field: str,
    invalid_value: object,
    expected_field: str,
) -> None:
    raw_case = serialized_case("same-error")
    raw_case[invalid_field] = invalid_value
    path = tmp_path / "same-error.jsonl"
    write_jsonl(path, [raw_case])

    with pytest.raises(EvaluationCaseValidationError) as direct_caught:
        EvaluationCase.from_mapping(raw_case)
    with pytest.raises(DatasetError) as loader_caught:
        load_dataset(path)

    assert loader_caught.value.field == direct_caught.value.field
    assert loader_caught.value.field == expected_field
    assert loader_caught.value.reason == direct_caught.value.reason
    assert loader_caught.value.case_id == "same-error"
    assert loader_caught.value.line_number == 1
    assert loader_caught.value.record_number == 1


@pytest.mark.parametrize(
    ("version_fragment", "expected_reason"),
    [
        ('"schema_version":"2",', "unsupported version '2'"),
        ("", "is required"),
    ],
)
def test_unsupported_and_missing_versions_are_rejected_by_loader(
    tmp_path: Path, version_fragment: str, expected_reason: str
) -> None:
    path = tmp_path / "version.jsonl"
    path.write_text("{" + version_fragment + '"id":"case","input":"text"}\n', encoding="utf-8")

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert caught.value.field == "schema_version"
    assert expected_reason in caught.value.reason


def test_duplicate_case_identifier_reports_both_locations(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.jsonl"
    path.write_text(
        json.dumps(serialized_case("duplicate"))
        + "\n\n"
        + json.dumps(serialized_case("duplicate"))
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value) == (
        f"{path}: line 3, record 2, case 'duplicate': field 'id': duplicate case identifier "
        "'duplicate' (first seen at line 1)"
    )
    assert caught.value.case_id == "duplicate"


@pytest.mark.parametrize("json_value", ["[]", '"text"', "1", "true", "null"])
def test_non_object_json_record_is_rejected_with_root_field(
    tmp_path: Path, json_value: str
) -> None:
    path = tmp_path / "array.jsonl"
    path.write_text(json_value + "\n", encoding="utf-8")

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value) == (f"{path}: line 1, record 1: field '$': must be a JSON object")


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_standard_json_number_is_rejected(tmp_path: Path, constant: str) -> None:
    path = tmp_path / "non-finite.jsonl"
    path.write_text(
        '{"schema_version":"1","id":"case","input":"text","metadata":{"x":' + constant + "}}\n",
        encoding="utf-8",
    )

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert caught.value.line_number == 1
    assert caught.value.record_number == 1
    assert caught.value.case_id is None
    assert caught.value.field is None
    assert caught.value.reason == (
        f"malformed JSON: non-standard numeric constant {constant!r} is not allowed"
    )
    assert isinstance(caught.value.__cause__, ValueError)


def test_duplicate_json_object_key_is_rejected_instead_of_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-key.jsonl"
    path.write_text(
        '{"schema_version":"1","id":"first","id":"second","input":"text"}\n',
        encoding="utf-8",
    )

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert caught.value.line_number == 1
    assert caught.value.record_number == 1
    assert "duplicate object key 'id' is not allowed" in caught.value.reason


def test_invalid_utf8_is_reported_as_dataset_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid-utf8.jsonl"
    path.write_bytes(b'\xff\xfe{"schema_version":"1"}')

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value).startswith(f"{path}: unable to decode dataset as UTF-8:")
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)


def test_missing_file_is_reported_as_dataset_error(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"

    with pytest.raises(DatasetError) as caught:
        load_dataset(path)

    assert str(caught.value).startswith(f"{path}: unable to read dataset:")
    assert isinstance(caught.value.__cause__, FileNotFoundError)
