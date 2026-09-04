"""Project-level errors for evaluation cases and datasets."""

from pathlib import Path


class EvaluationCaseValidationError(ValueError):
    """Raised when one evaluation-case mapping violates the supported schema."""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"field '{field}': {reason}")


class DatasetError(ValueError):
    """Raised when an evaluation dataset cannot be loaded in full."""

    def __init__(
        self,
        path: Path,
        reason: str,
        *,
        line_number: int | None = None,
        record_number: int | None = None,
        case_id: str | None = None,
        field: str | None = None,
    ) -> None:
        self.path = path
        self.reason = reason
        self.line_number = line_number
        self.record_number = record_number
        self.case_id = case_id
        self.field = field

        location = str(path)
        if line_number is not None:
            location += f": line {line_number}"
        if record_number is not None:
            location += f", record {record_number}"
        if case_id is not None:
            location += f", case {case_id!r}"
        if field is not None:
            location += f": field '{field}'"
        super().__init__(f"{location}: {reason}")
