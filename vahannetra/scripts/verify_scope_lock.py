from __future__ import annotations

import os
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

    print(f"strategy={SCOPE_LOCK.strategy}")
    print(f"source_root={SCOPE_LOCK.source_root}")
    print(f"target_root={SCOPE_LOCK.target_root}")

    if missing_source:
        print("missing_source_paths=")
        for item in missing_source:
            print(f"  - {item}")

    if missing_target:
        print("missing_target_paths=")
        for item in missing_target:
            print(f"  - {item}")

    if missing_source or missing_target:
        return 1

    print("scope_lock_verification=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
