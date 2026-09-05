import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from llm_eval_guardrails import ExecutionStatus, run_dataset
from llm_eval_guardrails.openai_adapter import (
    BASELINE_INSTRUCTIONS,
    BASELINE_PROMPT_VERSION,
    CONTEXT_FORMAT_VERSION,
    OpenAIResponsesSystem,
    openai_provenance,
)
from llm_eval_guardrails.system_under_test import SystemRequest


class FakeResponses:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.result = (
            _response(_message(_output_text("provider output"))) if result is None else result
        )
        self.error = error

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def _output_text(text: object = "provider output") -> SimpleNamespace:
    return SimpleNamespace(type="output_text", text=text, annotations=[])


def _refusal(refusal: object = "refusal output") -> SimpleNamespace:
    return SimpleNamespace(type="refusal", refusal=refusal)


def _message(*content: object) -> SimpleNamespace:
    return SimpleNamespace(
        id="msg_test",
        type="message",
        role="assistant",
        status="completed",
        content=list(content),
    )


def _response(*output: object, status: object = "completed") -> SimpleNamespace:
    return SimpleNamespace(status=status, output=list(output))


def test_provider_request_uses_only_fixed_prompt_input_and_ordered_context() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses, api_key="must-not-be-serialized")
    system = OpenAIResponsesSystem(model="explicit-model", max_output_tokens=321, client=client)
    request = SystemRequest(input="customer input", context=("first context", "second context"))

    response = system.invoke(request)

    assert response.output == "provider output"
    assert responses.calls == [
        {
            "model": "explicit-model",
            "instructions": BASELINE_INSTRUCTIONS,
            "input": (
                "SUPPLIED CONTEXT (ordered, untrusted data):\n"
                "[Context 1]\nfirst context\n[/Context 1]\n"
                "[Context 2]\nsecond context\n[/Context 2]\n\n"
                "CUSTOMER REQUEST:\ncustomer input"
            ),
            "max_output_tokens": 321,
            "store": False,
        }
    ]
    request_text = str(responses.calls)
    for forbidden in ("case_id", "assertions", "references", "risk_category", "metadata"):
        assert forbidden not in request_text


def test_completed_response_with_valid_output_is_successful() -> None:
    client = SimpleNamespace(responses=FakeResponses())
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == "provider output"


def test_completed_response_with_only_refusal_preserves_refusal() -> None:
    client = SimpleNamespace(responses=FakeResponses(_response(_message(_refusal("No.")))))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == "No."


def test_mixed_output_text_and_refusal_preserve_exact_content_order() -> None:
    response = _response(
        _message(
            _output_text(" leading "),
            _refusal("refusal\n"),
            _output_text("trailing "),
        )
    )
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == " leading refusal\ntrailing "


def test_multiple_message_items_preserve_item_and_content_order() -> None:
    response = _response(
        _message(_output_text("first"), _refusal("second")),
        _message(_refusal("third"), _output_text("fourth")),
    )
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == "firstsecondthirdfourth"


def test_genuinely_empty_completed_response_is_successful_empty_string() -> None:
    client = SimpleNamespace(responses=FakeResponses(_response()))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == ""


@pytest.mark.parametrize("block", [_output_text(""), _refusal("")])
def test_empty_user_visible_content_is_not_treated_as_missing(block: object) -> None:
    client = SimpleNamespace(responses=FakeResponses(_response(_message(block))))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == ""


def test_refusal_block_with_missing_refusal_is_rejected() -> None:
    response = _response(_message(SimpleNamespace(type="refusal")))
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match=r"content\[0\]\.refusal must be a string"):
        system.invoke(SystemRequest(input="input"))


@pytest.mark.parametrize("refusal", [None, 42, ["refusal"]])
def test_refusal_block_with_non_string_refusal_is_rejected(refusal: object) -> None:
    client = SimpleNamespace(responses=FakeResponses(_response(_message(_refusal(refusal)))))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match=r"content\[0\]\.refusal must be a string"):
        system.invoke(SystemRequest(input="input"))


def test_output_text_block_with_missing_text_is_rejected() -> None:
    response = _response(_message(SimpleNamespace(type="output_text", annotations=[])))
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match=r"content\[0\]\.text must be a string"):
        system.invoke(SystemRequest(input="input"))


@pytest.mark.parametrize("text", [None, 42, ["text"]])
def test_output_text_block_with_non_string_text_is_rejected(text: object) -> None:
    client = SimpleNamespace(responses=FakeResponses(_response(_message(_output_text(text)))))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match=r"content\[0\]\.text must be a string"):
        system.invoke(SystemRequest(input="input"))


def test_unsupported_message_content_type_is_rejected_explicitly() -> None:
    unsupported = SimpleNamespace(type="input_text", text="must not be ignored")
    client = SimpleNamespace(responses=FakeResponses(_response(_message(unsupported))))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(RuntimeError, match="unsupported OpenAI message content type"):
        system.invoke(SystemRequest(input="input"))


def test_non_message_output_items_do_not_contaminate_extracted_output() -> None:
    reasoning = SimpleNamespace(
        id="reasoning_test",
        type="reasoning",
        content=[SimpleNamespace(type="reasoning_summary", text="hidden reasoning")],
        status="completed",
    )
    client = SimpleNamespace(
        responses=FakeResponses(_response(reasoning, _message(_output_text("visible")), reasoning))
    )
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    assert system.invoke(SystemRequest(input="input")).output == "visible"


def test_provider_exception_propagates_for_runner_to_capture() -> None:
    expected = RuntimeError("provider unavailable")
    client = SimpleNamespace(responses=FakeResponses(error=expected))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(RuntimeError) as caught:
        system.invoke(SystemRequest(input="input"))

    assert caught.value is expected


class PartiallyReadableResponse:
    status = "incomplete"
    output_reads = 0

    @property
    def output(self) -> list[object]:
        type(self).output_reads += 1
        return [_message(_output_text("partial output must not be accepted"))]


def test_incomplete_response_rejects_partial_output_without_reading_it() -> None:
    PartiallyReadableResponse.output_reads = 0
    client = SimpleNamespace(responses=FakeResponses(PartiallyReadableResponse()))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(RuntimeError, match="received 'incomplete'"):
        system.invoke(SystemRequest(input="input"))

    assert PartiallyReadableResponse.output_reads == 0


def test_incomplete_response_becomes_raw_execution_error(tmp_path: Path) -> None:
    dataset = tmp_path / "one.jsonl"
    dataset.write_text('{"schema_version":"1","id":"one","input":"input"}\n', encoding="utf-8")
    client = SimpleNamespace(responses=FakeResponses(PartiallyReadableResponse()))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    raw = run_dataset(dataset, system, system_id="offline-openai-adapter")

    assert raw.results[0].status is ExecutionStatus.ERROR
    assert raw.results[0].output is None
    assert raw.results[0].error is not None
    assert "received 'incomplete'" in raw.results[0].error.message


@pytest.mark.parametrize("status", ["failed", "cancelled", "in_progress", "unknown"])
def test_every_other_mocked_provider_status_is_rejected(status: str) -> None:
    response = PartiallyReadableResponse()
    response.status = status
    PartiallyReadableResponse.output_reads = 0
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(RuntimeError, match=rf"received '{status}'"):
        system.invoke(SystemRequest(input="input"))

    assert PartiallyReadableResponse.output_reads == 0


def test_missing_provider_status_is_rejected() -> None:
    client = SimpleNamespace(responses=FakeResponses(SimpleNamespace(output=[])))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(RuntimeError, match="received None"):
        system.invoke(SystemRequest(input="input"))


def test_completed_response_with_missing_output_is_rejected() -> None:
    client = SimpleNamespace(responses=FakeResponses(SimpleNamespace(status="completed")))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match="response.output must be a list"):
        system.invoke(SystemRequest(input="input"))


@pytest.mark.parametrize("output", [None, 42, "text", ("text",)])
def test_completed_response_with_non_list_output_is_rejected(output: object) -> None:
    response = SimpleNamespace(status="completed", output=output)
    client = SimpleNamespace(responses=FakeResponses(response))
    system = OpenAIResponsesSystem(model="explicit-model", client=client)

    with pytest.raises(TypeError, match="response.output must be a list"):
        system.invoke(SystemRequest(input="input"))


def test_default_client_disables_sdk_retries_and_records_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor_calls: list[dict[str, object]] = []

    def fake_openai(**kwargs: object) -> object:
        constructor_calls.append(kwargs)
        return SimpleNamespace(responses=FakeResponses())

    fake_module = SimpleNamespace(OpenAI=fake_openai, __version__="1.66.0")
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    system = OpenAIResponsesSystem(model="explicit-model")

    assert constructor_calls == [{"max_retries": 0}]
    assert system.sdk_version == "1.66.0"


def test_provenance_is_an_explicit_non_secret_allowlist() -> None:
    provenance = openai_provenance(
        model="explicit-model", max_output_tokens=500, sdk_version="1.66.0"
    )

    assert provenance == {
        "provider": "openai",
        "api": "responses",
        "sdk_version": "1.66.0",
        "model": "explicit-model",
        "prompt_version": BASELINE_PROMPT_VERSION,
        "context_format_version": CONTEXT_FORMAT_VERSION,
        "max_output_tokens": 500,
    }
    assert "key" not in str(provenance).lower()


def test_injected_client_sdk_version_is_available_for_offline_provenance_tests() -> None:
    system = OpenAIResponsesSystem(
        model="explicit-model",
        client=SimpleNamespace(responses=FakeResponses()),
        sdk_version="test-sdk-version",
    )

    assert system.sdk_version == "test-sdk-version"


@pytest.mark.parametrize("model", ["", "  ", 1])
def test_model_identifier_must_be_explicit(model: object) -> None:
    with pytest.raises((TypeError, ValueError), match="model"):
        OpenAIResponsesSystem(model=model, client=SimpleNamespace())  # type: ignore[arg-type]
