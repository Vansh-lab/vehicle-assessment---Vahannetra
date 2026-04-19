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
    missing_files = [
        file_path
        for file_path in _REQUIRED_FRONTEND_FILES
        if not (repo_root / file_path).exists()
    ]

    payload = {
        "phase": "phase4",
        "artifact_root": str(Path(__file__).resolve().parents[1]),
        "required_routes": sorted(_REQUIRED_ROUTES),
        "missing_routes": missing_routes,
        "required_frontend_files": _REQUIRED_FRONTEND_FILES,
        "missing_frontend_files": missing_files,
        "status": "ok"
        if not missing_routes and not missing_files
        else "missing_artifacts",
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
