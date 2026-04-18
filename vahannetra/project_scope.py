from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeLock:
    strategy: str
    source_root: str
    target_root: str
    backend_source: str
    frontend_source: str
    infra_source: str


SCOPE_LOCK = ScopeLock(
    strategy="incremental_upgrade",
    source_root="/home/runner/work/vehicle-assessment---Vahannetra/vehicle-assessment---Vahannetra",
    target_root="vahannetra",
    backend_source="FDA_Project/vehicle_assessment_backend",
    frontend_source="FDA_Project/vahannetra_frontend",
    infra_source="FDA_Project",
)

TARGET_DIRECTORY_MAP: dict[str, str] = {
    "backend": "vahannetra/backend",
    "backend_app": "vahannetra/backend/app",
    "backend_ml": "vahannetra/backend/ml",
    "backend_tests": "vahannetra/backend/tests",
    "frontend": "vahannetra/frontend",
    "frontend_src": "vahannetra/frontend/src",
    "migrations": "vahannetra/migrations",
    "scripts": "vahannetra/scripts",
    "infra": "vahannetra/infra",
    "infra_k8s": "vahannetra/infra/k8s",
    "github_workflows": ".github/workflows",
}
