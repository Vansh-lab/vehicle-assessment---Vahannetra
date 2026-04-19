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

_REQUIRED_FRONTEND_FILES = [
    "vahannetra/frontend/README.md",
    "vahannetra/frontend/src/lib/env.ts",
    "vahannetra/frontend/src/lib/api.ts",
    "vahannetra/frontend/src/types/assessment.ts",
]

_REQUIRED_INFRA_FILES = [
    "vahannetra/infra/README.md",
    "vahannetra/infra/k8s/namespace.yaml",
    "vahannetra/infra/k8s/api-deployment.yaml",
    "vahannetra/infra/k8s/frontend-deployment.yaml",
    "vahannetra/infra/k8s/worker-deployment.yaml",
]

_REQUIRED_WORKFLOWS = [
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/deploy-ecs.yml",
]

_REQUIRED_RUNTIME_PROOF_DOCS = [
    "FDA_Project/aws-runtime-proof-runbook.md",
    "FDA_Project/operator-mode-runtime-proof.md",
    "FDA_Project/phase-c-closure-audit.md",
]

_REQUIRED_DEPLOY_WORKFLOW_MARKERS = [
    "health-gates:",
    "rollback-on-failure:",
    "Upload perf evidence artifact",
]

_REQUIRED_CODEQL_WORKFLOW_MARKERS = [
    "CodeQL Security Scan",
    "language: [\"javascript-typescript\", \"python\"]",
]

_REQUIRED_OPERATOR_CLOSURE_MARKERS = [
    "## 6) Final closure criteria (single source)",
    "- [ ] Success-path live ECS deploy evidence captured",
    "- [ ] Rollback-path live recovery evidence captured",
    "- [ ] CodeQL jobs actually execute (no zero-job `action_required`)",
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
    missing_frontend_files = _find_missing_paths(repo_root, _REQUIRED_FRONTEND_FILES)
    missing_infra_files = _find_missing_paths(repo_root, _REQUIRED_INFRA_FILES)
    missing_workflows = _find_missing_paths(repo_root, _REQUIRED_WORKFLOWS)
    missing_runtime_proof_docs = _find_missing_paths(repo_root, _REQUIRED_RUNTIME_PROOF_DOCS)

    deploy_workflow_path = repo_root / ".github/workflows/deploy-ecs.yml"
    codeql_workflow_path = repo_root / ".github/workflows/codeql.yml"
    operator_proof_path = repo_root / "FDA_Project/operator-mode-runtime-proof.md"

    missing_deploy_workflow_markers = _find_missing_markers(
        deploy_workflow_path, _REQUIRED_DEPLOY_WORKFLOW_MARKERS
    )
    missing_codeql_workflow_markers = _find_missing_markers(
        codeql_workflow_path, _REQUIRED_CODEQL_WORKFLOW_MARKERS
    )
    missing_operator_closure_markers = _find_missing_markers(
        operator_proof_path, _REQUIRED_OPERATOR_CLOSURE_MARKERS
    )

    payload = {
        "phase": "phase6",
        "artifact_root": str(repo_root),
        "required_routes": sorted(_REQUIRED_ROUTES),
        "missing_routes": missing_routes,
        "required_frontend_files": _REQUIRED_FRONTEND_FILES,
        "missing_frontend_files": missing_frontend_files,
        "required_infra_files": _REQUIRED_INFRA_FILES,
        "missing_infra_files": missing_infra_files,
        "required_workflows": _REQUIRED_WORKFLOWS,
        "missing_workflows": missing_workflows,
        "required_runtime_proof_docs": _REQUIRED_RUNTIME_PROOF_DOCS,
        "missing_runtime_proof_docs": missing_runtime_proof_docs,
        "required_deploy_workflow_markers": _REQUIRED_DEPLOY_WORKFLOW_MARKERS,
        "missing_deploy_workflow_markers": missing_deploy_workflow_markers,
        "required_codeql_workflow_markers": _REQUIRED_CODEQL_WORKFLOW_MARKERS,
        "missing_codeql_workflow_markers": missing_codeql_workflow_markers,
        "required_operator_closure_markers": _REQUIRED_OPERATOR_CLOSURE_MARKERS,
        "missing_operator_closure_markers": missing_operator_closure_markers,
        "status": "ok"
        if not missing_routes
        and not missing_frontend_files
        and not missing_infra_files
        and not missing_workflows
        and not missing_runtime_proof_docs
        and not missing_deploy_workflow_markers
        and not missing_codeql_workflow_markers
        and not missing_operator_closure_markers
        else "missing_artifacts",
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
