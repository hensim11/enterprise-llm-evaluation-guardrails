"""Typed domain representation and validation for evaluation cases."""

from __future__ import annotations

import math
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TypeAlias

from llm_eval_guardrails.case_schema import (
    EVALUATION_CASE_SCHEMA_VERSION,
    SUPPORTED_EVALUATION_CASE_SCHEMA_VERSIONS,
    AssertionType,
    RiskCategory,
)
from llm_eval_guardrails.errors import EvaluationCaseValidationError

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_CASE_FIELDS = frozenset(
    {
        "schema_version",
        "id",
        "input",
        "context",
        "references",
        "tags",
        "risk_category",
        "expected_behavior",
        "assertions",
        "metadata",
    }
)
_ASSERTION_FIELDS = frozenset({"criterion", "type", "value"})


@dataclass(frozen=True, slots=True)
class EvaluationAssertion:
    """One named, deterministic expectation attached to an evaluation case."""

    criterion: str
    type: AssertionType
    value: str

    def __post_init__(self) -> None:
        _non_empty_string(self.criterion, "criterion")
        if not isinstance(self.type, AssertionType):
            raise EvaluationCaseValidationError("type", "must be an AssertionType")
        _non_empty_string(self.value, "value")

    def to_mapping(self) -> dict[str, str]:
        """Return the assertion in its serialized shape."""
        return {"criterion": self.criterion, "type": self.type.value, "value": self.value}


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """A validated v1 evaluation case with shallowly frozen attributes."""

    id: str
    input: str
    schema_version: str = EVALUATION_CASE_SCHEMA_VERSION
    context: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    risk_category: RiskCategory | None = None
    expected_behavior: str | None = None
    assertions: tuple[EvaluationAssertion, ...] = ()
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        schema_version = _non_empty_string(self.schema_version, "schema_version")
        _ensure_supported_schema_version(schema_version)
        _non_empty_string(self.id, "id")
        _non_empty_string(self.input, "input")
        _validate_domain_string_tuple(self.context, "context")
        _validate_domain_string_tuple(self.references, "references")
        _validate_domain_string_tuple(self.tags, "tags", require_unique=True)

        if self.risk_category is not None and not isinstance(self.risk_category, RiskCategory):
            raise EvaluationCaseValidationError("risk_category", "must be a RiskCategory")
        if self.expected_behavior is not None:
            _non_empty_string(self.expected_behavior, "expected_behavior")

        if not isinstance(self.assertions, tuple):
            raise EvaluationCaseValidationError("assertions", "must be a tuple")
        first_criterion_index: dict[str, int] = {}
        for index, assertion in enumerate(self.assertions):
            if not isinstance(assertion, EvaluationAssertion):
                raise EvaluationCaseValidationError(
                    f"assertions[{index}]", "must be an EvaluationAssertion"
                )
            if assertion.criterion in first_criterion_index:
                original_index = first_criterion_index[assertion.criterion]
                raise EvaluationCaseValidationError(
                    f"assertions[{index}].criterion",
                    f"duplicates assertions[{original_index}].criterion value "
                    f"{assertion.criterion!r}",
                )
            first_criterion_index[assertion.criterion] = index

        object.__setattr__(self, "metadata", _parse_metadata(self.metadata))

    @classmethod
    def from_mapping(cls, value: object) -> EvaluationCase:
        """Validate a mapping without mutating it and return a typed case."""
        if not isinstance(value, Mapping):
            raise EvaluationCaseValidationError("$", "must be a JSON object")

        schema_version = _required_string(value, "schema_version")
        _ensure_supported_schema_version(schema_version)

        _reject_unknown_fields(value, _CASE_FIELDS, "$", top_level=True)

        case_id = _required_string(value, "id")
        case_input = _required_string(value, "input")
        context = _optional_string_list(value, "context")
        references = _optional_string_list(value, "references")
        tags = _optional_string_list(value, "tags", require_unique=True)

        risk_category = None
        if "risk_category" in value:
            risk_category_text = _non_empty_string(value["risk_category"], "risk_category")
            try:
                risk_category = RiskCategory(risk_category_text)
            except ValueError as error:
                allowed = ", ".join(repr(category.value) for category in RiskCategory)
                raise EvaluationCaseValidationError(
                    "risk_category", f"must be one of: {allowed}"
                ) from error

        expected_behavior = None
        if "expected_behavior" in value:
            expected_behavior = _non_empty_string(value["expected_behavior"], "expected_behavior")

        assertions = _parse_assertions(value.get("assertions", []))
        metadata = _parse_metadata(value.get("metadata", {}))

        return cls(
            schema_version=schema_version,
            id=case_id,
            input=case_input,
            context=context,
            references=references,
            tags=tags,
            risk_category=risk_category,
            expected_behavior=expected_behavior,
            assertions=assertions,
            metadata=metadata,
        )

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible mapping, omitting absent optional fields."""
        result: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "input": self.input,
        }
        if self.context:
            result["context"] = list(self.context)
        if self.references:
            result["references"] = list(self.references)
        if self.tags:
            result["tags"] = list(self.tags)
        if self.risk_category is not None:
            result["risk_category"] = self.risk_category.value
        if self.expected_behavior is not None:
            result["expected_behavior"] = self.expected_behavior
        if self.assertions:
            result["assertions"] = [assertion.to_mapping() for assertion in self.assertions]
        if self.metadata:
            result["metadata"] = deepcopy(dict(self.metadata))
        return result


def _required_string(value: Mapping[str, object], field_name: str) -> str:
    if field_name not in value:
        raise EvaluationCaseValidationError(field_name, "is required")
    return _non_empty_string(value[field_name], field_name)


def _ensure_supported_schema_version(schema_version: str) -> None:
    if schema_version not in SUPPORTED_EVALUATION_CASE_SCHEMA_VERSIONS:
        supported = ", ".join(
            repr(version) for version in sorted(SUPPORTED_EVALUATION_CASE_SCHEMA_VERSIONS)
        )
        raise EvaluationCaseValidationError(
            "schema_version",
            f"unsupported version {schema_version!r}; supported versions: {supported}",
        )


def _non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise EvaluationCaseValidationError(field_name, "must be a string")
    if not value.strip():
        raise EvaluationCaseValidationError(field_name, "must be a non-empty string")
    return value


def _optional_string_list(
    value: Mapping[str, object], field_name: str, *, require_unique: bool = False
) -> tuple[str, ...]:
    raw_items = value.get(field_name, [])
    if not isinstance(raw_items, list):
        raise EvaluationCaseValidationError(field_name, "must be an array")

    items = tuple(
        _non_empty_string(item, f"{field_name}[{index}]") for index, item in enumerate(raw_items)
    )
    if require_unique:
        first_index: dict[str, int] = {}
        for index, item in enumerate(items):
            if item in first_index:
                raise EvaluationCaseValidationError(
                    f"{field_name}[{index}]",
                    f"duplicates {field_name}[{first_index[item]}] value {item!r}",
                )
            first_index[item] = index
    return items


def _validate_domain_string_tuple(
    value: object, field_name: str, *, require_unique: bool = False
) -> None:
    if not isinstance(value, tuple):
        raise EvaluationCaseValidationError(field_name, "must be a tuple")

    first_index: dict[str, int] = {}
    for index, item in enumerate(value):
        item = _non_empty_string(item, f"{field_name}[{index}]")
        if require_unique and item in first_index:
            raise EvaluationCaseValidationError(
                f"{field_name}[{index}]",
                f"duplicates {field_name}[{first_index[item]}] value {item!r}",
            )
        first_index[item] = index


def _parse_assertions(value: object) -> tuple[EvaluationAssertion, ...]:
    if not isinstance(value, list):
        raise EvaluationCaseValidationError("assertions", "must be an array")

    assertions: list[EvaluationAssertion] = []
    first_criterion_index: dict[str, int] = {}
    for index, raw_assertion in enumerate(value):
        path = f"assertions[{index}]"
        if not isinstance(raw_assertion, Mapping):
            raise EvaluationCaseValidationError(path, "must be a JSON object")
        _reject_unknown_fields(raw_assertion, _ASSERTION_FIELDS, path)

        criterion = _required_nested_string(raw_assertion, "criterion", path)
        assertion_type_text = _required_nested_string(raw_assertion, "type", path)
        assertion_value = _required_nested_string(raw_assertion, "value", path)
        try:
            assertion_type = AssertionType(assertion_type_text)
        except ValueError as error:
            allowed = ", ".join(repr(assertion_type.value) for assertion_type in AssertionType)
            raise EvaluationCaseValidationError(
                f"{path}.type", f"must be one of: {allowed}"
            ) from error

        if criterion in first_criterion_index:
            raise EvaluationCaseValidationError(
                f"{path}.criterion",
                f"duplicates assertions[{first_criterion_index[criterion]}].criterion "
                f"value {criterion!r}",
            )
        first_criterion_index[criterion] = index
        assertions.append(EvaluationAssertion(criterion, assertion_type, assertion_value))
    return tuple(assertions)


def _required_nested_string(value: Mapping[str, object], field_name: str, parent_path: str) -> str:
    path = f"{parent_path}.{field_name}"
    if field_name not in value:
        raise EvaluationCaseValidationError(path, "is required")
    return _non_empty_string(value[field_name], path)


def _parse_metadata(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise EvaluationCaseValidationError("metadata", "must be a JSON object")
    result: dict[str, JsonValue] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise EvaluationCaseValidationError("metadata", "object keys must be strings")
        result[key] = _copy_json_value(item, f"metadata.{key}")
    return result


def _copy_json_value(value: object, path: str) -> JsonValue:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvaluationCaseValidationError(path, "must be a finite JSON number")
        return value
    if isinstance(value, list):
        return [_copy_json_value(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise EvaluationCaseValidationError(path, "object keys must be strings")
            result[key] = _copy_json_value(item, f"{path}.{key}")
        return result
    raise EvaluationCaseValidationError(path, "must be a JSON value")


def _reject_unknown_fields(
    value: Mapping[str, object],
    allowed_fields: frozenset[str],
    parent_path: str,
    *,
    top_level: bool = False,
) -> None:
    if any(not isinstance(key, str) for key in value):
        raise EvaluationCaseValidationError(parent_path, "object keys must be strings")
    unknown_fields = sorted(key for key in value if key not in allowed_fields)
    if unknown_fields:
        unknown = unknown_fields[0]
        field_path = unknown if top_level else f"{parent_path}.{unknown}"
        raise EvaluationCaseValidationError(field_path, "is not allowed")
