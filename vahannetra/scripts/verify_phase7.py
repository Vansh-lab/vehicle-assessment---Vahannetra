from __future__ import annotations

import json
import sys
from pathlib import Path

from vahannetra.backend.app.main import app

_REQUIRED_ROUTES = {
    "/",
    "/health",
    "/api/v1/analyze",
    "/api/v1/analyze/url",
    "/api/v1/analyze/video",
    "/api/v1/results/{job_id}",
    "/api/v1/system/capabilities",
    "/api/v1/system/me",
}

_REQUIRED_PHASE_SCRIPTS = [
    "vahannetra/scripts/verify_scope_lock.py",
    "vahannetra/scripts/verify_phase2_backend.py",
    "vahannetra/scripts/verify_phase3_backend.py",
    "vahannetra/scripts/verify_phase4.py",
    "vahannetra/scripts/verify_phase5.py",
    "vahannetra/scripts/verify_phase6.py",
]

_REQUIRED_WORKFLOWS = [
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/deploy-ecs.yml",
]

_REQUIRED_PHASE_DOCS = [
    "FDA_Project/aws-runtime-proof-runbook.md",
    "FDA_Project/operator-mode-runtime-proof.md",
    "FDA_Project/phase-c-closure-audit.md",
]

_REQUIRED_CI_MARKERS = [
    "name: CI",
    "push:",
    "pull_request:",
    'branches: ["main", "master", "copilot/**"]',
    'branches: ["main", "master"]',
    "lint:",
    "test:",
    "build:",
    "deploy:",
    "needs: [test, lint]",
    "needs: [build]",
]

_REQUIRED_DEPLOY_MARKERS = [
    "name: Deploy ECS/ECR",
    "workflow_dispatch:",
    "health-gates:",
    "rollback-on-failure:",
]

_REQUIRED_CODEQL_MARKERS = [
    "name: CodeQL Security Scan",
    "pull_request:",
    'language: ["javascript-typescript", "python"]',
]


def _find_missing_paths(repo_root: Path, required: list[str]) -> list[str]:
    return [item for item in required if not (repo_root / item).exists()]


def _find_missing_markers(file_path: Path, required_markers: list[str]) -> list[str]:
    if not file_path.exists():
        return required_markers
    content = file_path.read_text(encoding="utf-8")
    return [marker for marker in required_markers if marker not in content]


def main() -> int:
    route_paths = sorted(
        {
            route.path
            for route in app.routes
            if getattr(route, "path", "").startswith("/")
        }
    )
    missing_routes = sorted(_REQUIRED_ROUTES.difference(set(route_paths)))

    repo_root = Path(__file__).resolve().parents[2]
    missing_phase_scripts = _find_missing_paths(repo_root, _REQUIRED_PHASE_SCRIPTS)
    missing_workflows = _find_missing_paths(repo_root, _REQUIRED_WORKFLOWS)
    missing_phase_docs = _find_missing_paths(repo_root, _REQUIRED_PHASE_DOCS)

    ci_workflow_path = repo_root / ".github/workflows/ci.yml"
    deploy_workflow_path = repo_root / ".github/workflows/deploy-ecs.yml"
    codeql_workflow_path = repo_root / ".github/workflows/codeql.yml"

    missing_ci_markers = _find_missing_markers(ci_workflow_path, _REQUIRED_CI_MARKERS)
    missing_deploy_markers = _find_missing_markers(
        deploy_workflow_path, _REQUIRED_DEPLOY_MARKERS
    )
    missing_codeql_markers = _find_missing_markers(
        codeql_workflow_path, _REQUIRED_CODEQL_MARKERS
    )

    payload = {
        "phase": "phase7",
        "artifact_root": str(repo_root),
        "required_routes": sorted(_REQUIRED_ROUTES),
        "missing_routes": missing_routes,
        "required_phase_scripts": _REQUIRED_PHASE_SCRIPTS,
        "missing_phase_scripts": missing_phase_scripts,
        "required_workflows": _REQUIRED_WORKFLOWS,
        "missing_workflows": missing_workflows,
        "required_phase_docs": _REQUIRED_PHASE_DOCS,
        "missing_phase_docs": missing_phase_docs,
        "required_ci_markers": _REQUIRED_CI_MARKERS,
        "missing_ci_markers": missing_ci_markers,
        "required_deploy_markers": _REQUIRED_DEPLOY_MARKERS,
        "missing_deploy_markers": missing_deploy_markers,
        "required_codeql_markers": _REQUIRED_CODEQL_MARKERS,
        "missing_codeql_markers": missing_codeql_markers,
        "status": "ok"
        if not missing_routes
        and not missing_phase_scripts
        and not missing_workflows
        and not missing_phase_docs
        and not missing_ci_markers
        and not missing_deploy_markers
        and not missing_codeql_markers
        else "missing_artifacts",
    }

    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
