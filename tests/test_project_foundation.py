from pathlib import Path

import llm_eval_guardrails

ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_version() -> None:
    assert llm_eval_guardrails.__version__ == "0.1.0"


def test_core_project_documents_exist() -> None:
    expected_documents = {
        "README.md",
        "PROJECT_VISION.md",
        "ROADMAP.md",
        "PROJECT_STATE.md",
        "DECISIONS.md",
        "docs/EVALUATION_SPEC.md",
        "docs/RUN_ARTIFACT_SPEC.md",
    }

    missing = [path for path in expected_documents if not (ROOT / path).is_file()]

    assert missing == []
