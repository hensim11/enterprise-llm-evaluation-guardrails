from dataclasses import fields
from re import escape

import pytest

from llm_eval_guardrails import (
    AssertionType,
    EchoSystemUnderTest,
    EvaluationAssertion,
    EvaluationCase,
    RiskCategory,
    SystemRequest,
    SystemResponse,
    SystemUnderTest,
)


def invoke(system: SystemUnderTest, request: SystemRequest) -> SystemResponse:
    return system.invoke(request)


def test_request_preserves_input_and_ordered_context_exactly() -> None:
    request = SystemRequest(
        input="  Keep surrounding whitespace.  ",
        context=(" second ", "first", "繰り返しなし"),
    )

    assert request.input == "  Keep surrounding whitespace.  "
    assert request.context == (" second ", "first", "繰り返しなし")


def test_request_contract_excludes_evaluation_only_fields() -> None:
    case = EvaluationCase(
        id="privacy-001",
        input="Do not expose the token.",
        context=("Token: SAMPLE-123",),
        references=("I cannot expose that token.",),
        tags=("privacy",),
        risk_category=RiskCategory.PRIVACY,
        expected_behavior="Do not reveal the supplied token.",
        assertions=(
            EvaluationAssertion(
                criterion="no-token",
                type=AssertionType.NOT_CONTAINS,
                value="SAMPLE-123",
            ),
        ),
        metadata={"source": "illustrative"},
    )

    request = SystemRequest(input=case.input, context=case.context)

    assert [field.name for field in fields(request)] == ["input", "context"]
    assert request == SystemRequest(
        input="Do not expose the token.", context=("Token: SAMPLE-123",)
    )


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        ({"input": 1}, TypeError, "input must be a string"),
        ({"input": ""}, ValueError, "input must be a non-empty string"),
        ({"input": "text", "context": ["context"]}, TypeError, "context must be a tuple"),
        (
            {"input": "text", "context": ("valid", 1)},
            TypeError,
            "context[1] must be a string",
        ),
        (
            {"input": "text", "context": ("valid", "  ")},
            ValueError,
            "context[1] must be a non-empty string",
        ),
    ],
)
def test_request_rejects_invalid_values_without_coercion(
    kwargs: dict[str, object], exception: type[Exception], message: str
) -> None:
    with pytest.raises(exception, match=escape(message)):
        SystemRequest(**kwargs)  # type: ignore[arg-type]


def test_echo_output_is_repeatable_and_preserves_input() -> None:
    system = EchoSystemUnderTest()
    request = SystemRequest(input="  exact input  ", context=("ignored",))

    first = system.invoke(request)
    second = system.invoke(request)

    assert first == second == SystemResponse(output="  exact input  ")


def test_empty_response_output_is_valid() -> None:
    assert SystemResponse(output="").output == ""


@pytest.mark.parametrize("invalid_output", [None, 1, b"text", ["text"]])
def test_non_string_response_output_is_rejected(invalid_output: object) -> None:
    with pytest.raises(TypeError, match="output must be a string"):
        SystemResponse(output=invalid_output)  # type: ignore[arg-type]


def test_structural_implementation_works_without_concrete_inheritance() -> None:
    class UppercaseSystem:
        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            return SystemResponse(output=request.input.upper())

    system = UppercaseSystem()

    assert isinstance(system, SystemUnderTest)
    assert invoke(system, SystemRequest(input="Mixed case")).output == "MIXED CASE"


def test_implementation_exception_propagates_unchanged() -> None:
    expected = RuntimeError("system unavailable")

    class FailingSystem:
        def invoke(self, request: SystemRequest, /) -> SystemResponse:
            raise expected

    with pytest.raises(RuntimeError) as caught:
        invoke(FailingSystem(), SystemRequest(input="Hello"))

    assert caught.value is expected
