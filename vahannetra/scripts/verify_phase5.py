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


def _find_missing_paths(repo_root: Path, required: list[str]) -> list[str]:
    return [item for item in required if not (repo_root / item).exists()]


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

    payload = {
        "phase": "phase5",
        "artifact_root": str(Path(__file__).resolve().parents[1]),
        "required_routes": sorted(_REQUIRED_ROUTES),
        "missing_routes": missing_routes,
        "required_frontend_files": _REQUIRED_FRONTEND_FILES,
        "missing_frontend_files": missing_frontend_files,
        "required_infra_files": _REQUIRED_INFRA_FILES,
        "missing_infra_files": missing_infra_files,
        "required_workflows": _REQUIRED_WORKFLOWS,
        "missing_workflows": missing_workflows,
        "status": "ok"
        if not missing_routes
        and not missing_frontend_files
        and not missing_infra_files
        and not missing_workflows
        else "missing_artifacts",
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
