"""Provider-agnostic contracts for invoking a system under test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SystemRequest:
    """Text and ordered context supplied to a system under test.

    Evaluation expectations and case metadata deliberately do not belong in this
    contract. A runner must retain those separately from the system input.
    """

    input: str
    context: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_non_empty_string(self.input, "input")
        if not isinstance(self.context, tuple):
            raise TypeError("context must be a tuple")
        for index, item in enumerate(self.context):
            _validate_non_empty_string(item, f"context[{index}]")


@dataclass(frozen=True, slots=True)
class SystemResponse:
    """Raw text returned by a system under test, including a valid empty string."""

    output: str

    def __post_init__(self) -> None:
        if not isinstance(self.output, str):
            raise TypeError("output must be a string")


@runtime_checkable
class SystemUnderTest(Protocol):
    """Synchronous structural interface for a model or application adapter.

    Implementations may raise ordinary exceptions. Callers must not reinterpret an
    exception as a successful response; per-case handling belongs to the runner.
    """

    def invoke(self, request: SystemRequest, /) -> SystemResponse:
        """Return the system response or propagate an implementation exception."""
        ...


@dataclass(frozen=True, slots=True)
class EchoSystemUnderTest:
    """Deterministic plumbing double that returns request input verbatim.

    Ordered context is accepted through the common request contract but intentionally
    ignored. This double does not simulate model intelligence, domain correctness, or
    safety behaviour.
    """

    def invoke(self, request: SystemRequest, /) -> SystemResponse:
        """Return the request input exactly, without trimming or coercion."""
        return SystemResponse(output=request.input)


def _validate_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
