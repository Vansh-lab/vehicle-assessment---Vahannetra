from __future__ import annotations

import json
import sys
from importlib.util import find_spec
from pathlib import Path

from vahannetra.backend.app.main import app


def main() -> int:
    route_paths = sorted(
        {
            route.path
            for route in app.routes
            if getattr(route, "path", "").startswith("/")
        }
    )

    required_routes = {
        "/",
        "/health",
        "/api/v1/analyze",
        "/api/v1/analyze/video",
        "/api/v1/results/{job_id}",
        "/api/v1/system/capabilities",
        "/api/v1/system/me",
    }
    missing_routes = sorted(required_routes.difference(set(route_paths)))

    required_modules = [
        "vahannetra.backend.app.models",
        "vahannetra.backend.app.services.jobs",
        "vahannetra.backend.app.services.storage",
        "vahannetra.backend.app.services.video_processing",
        "vahannetra.backend.app.tasks.celery_app",
        "vahannetra.backend.app.tasks.pipeline",
    ]
    missing_modules = [
        module_name for module_name in required_modules if find_spec(module_name) is None
    ]

    payload = {
        "phase": "phase3",
        "artifact_root": str(Path(__file__).resolve().parents[1]),
        "required_routes": sorted(required_routes),
        "discovered_routes": route_paths,
        "missing_routes": missing_routes,
        "required_modules": required_modules,
        "missing_modules": missing_modules,
        "status": "ok"
        if not missing_routes and not missing_modules
        else "missing_artifacts",
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
