from __future__ import annotations

import json
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

    required = {
        "/",
        "/health",
        "/api/v1/system/capabilities",
        "/api/v1/system/me",
        "/api/v1/analyze",
    }
    missing = sorted(required.difference(set(route_paths)))

    payload = {
        "phase": "phase2",
        "artifact_root": str(Path(__file__).resolve().parents[1]),
        "required_routes": sorted(required),
        "discovered_routes": route_paths,
        "missing_routes": missing,
        "status": "ok" if not missing else "missing_routes",
    }
    print(json.dumps(payload, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
