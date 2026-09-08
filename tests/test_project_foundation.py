import re
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
        "docs/EVALUATION_ARTIFACT_SPEC.md",
        "docs/BASELINE_WORKFLOW.md",
        "docs/BATCH_D_CONTRACT.md",
        "docs/PORTFOLIO_WALKTHROUGH.md",
        "docs/REPRODUCIBILITY.md",
        "docs/RUN_ARTIFACT_SPEC.md",
        "benchmarks/northstar_bank_v1.jsonl",
        "evidence/README.md",
        "scripts/verify_retained_evidence.py",
    }

    missing = [path for path in expected_documents if not (ROOT / path).is_file()]

    assert missing == []


def test_release_documentation_local_links_resolve() -> None:
    documents = (
        ROOT / "README.md",
        ROOT / "docs/REPRODUCIBILITY.md",
        ROOT / "docs/PORTFOLIO_WALKTHROUGH.md",
    )
    unresolved = []
    for document in documents:
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if not (document.parent / path).exists():
                unresolved.append(f"{document.relative_to(ROOT)} -> {target}")

    assert unresolved == []
