from __future__ import annotations

import json
import sys
from pathlib import Path

from vahannetra.project_scope import SCOPE_LOCK, TARGET_DIRECTORY_MAP


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_required_paths() -> tuple[list[str], list[str]]:
    repo_root = _repo_root()
    missing_source: list[str] = []
    missing_target: list[str] = []

    source_paths = [
        SCOPE_LOCK.backend_source,
        SCOPE_LOCK.frontend_source,
        SCOPE_LOCK.infra_source,
    ]

    for source in source_paths:
        if not (repo_root / source).exists():
            missing_source.append(source)

    for target in TARGET_DIRECTORY_MAP.values():
        if not (repo_root / target).exists():
            missing_target.append(target)

    return missing_source, missing_target


def main() -> int:
    missing_source, missing_target = verify_required_paths()
    status = "ok" if not missing_source and not missing_target else "missing_paths"
    payload = {
        "strategy": SCOPE_LOCK.strategy,
        "source_root": SCOPE_LOCK.source_root,
        "target_root": SCOPE_LOCK.target_root,
        "missing_source_paths": missing_source,
        "missing_target_paths": missing_target,
        "scope_lock_verification": status,
    }
    print(json.dumps(payload, indent=2))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
