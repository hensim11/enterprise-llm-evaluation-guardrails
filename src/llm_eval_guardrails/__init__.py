"""Evaluation and guardrail tooling for LLM applications."""

from llm_eval_guardrails.case_schema import (
    EVALUATION_CASE_SCHEMA_VERSION,
    AssertionType,
    RiskCategory,
)
from llm_eval_guardrails.dataset import load_dataset
from llm_eval_guardrails.errors import DatasetError, EvaluationCaseValidationError
from llm_eval_guardrails.evaluation_artifact import (
    EVALUATION_ARTIFACT_SCHEMA_VERSION,
    AssertionEvaluation,
    CaseEvaluationResult,
    EvaluationArtifact,
    EvaluationError,
    EvaluationOutcome,
    load_evaluation_artifact,
    write_evaluation_artifact,
)
from llm_eval_guardrails.evaluation_case import EvaluationAssertion, EvaluationCase
from llm_eval_guardrails.evaluator import evaluate_run
from llm_eval_guardrails.reporting import (
    AggregateReport,
    aggregate_run,
    render_markdown_report,
    validate_json_report,
    validate_markdown_report,
    write_json_report,
    write_markdown_report,
)
from llm_eval_guardrails.run_artifact import (
    RUN_ARTIFACT_SCHEMA_VERSION,
    CaseExecutionResult,
    DatasetProvenance,
    ExecutionError,
    ExecutionStatus,
    RunArtifact,
    SystemProvenance,
    load_run_artifact,
    write_run_artifact,
)
from llm_eval_guardrails.runner import run_dataset
from llm_eval_guardrails.system_under_test import (
    EchoSystemUnderTest,
    SystemRequest,
    SystemResponse,
    SystemUnderTest,
)

__version__ = "0.1.0"

__all__ = [
    "AssertionType",
    "AssertionEvaluation",
    "AggregateReport",
    "CaseExecutionResult",
    "DatasetError",
    "DatasetProvenance",
    "EVALUATION_CASE_SCHEMA_VERSION",
    "EVALUATION_ARTIFACT_SCHEMA_VERSION",
    "EchoSystemUnderTest",
    "ExecutionError",
    "ExecutionStatus",
    "EvaluationAssertion",
    "EvaluationArtifact",
    "EvaluationCase",
    "CaseEvaluationResult",
    "EvaluationError",
    "EvaluationOutcome",
    "EvaluationCaseValidationError",
    "RiskCategory",
    "RUN_ARTIFACT_SCHEMA_VERSION",
    "RunArtifact",
    "SystemRequest",
    "SystemResponse",
    "SystemUnderTest",
    "SystemProvenance",
    "__version__",
    "load_dataset",
    "load_evaluation_artifact",
    "load_run_artifact",
    "aggregate_run",
    "evaluate_run",
    "render_markdown_report",
    "run_dataset",
    "validate_json_report",
    "validate_markdown_report",
    "write_run_artifact",
    "write_evaluation_artifact",
    "write_json_report",
    "write_markdown_report",
]
