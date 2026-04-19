from __future__ import annotations

from pathlib import Path

from vahannetra.project_scope import TARGET_DIRECTORY_MAP


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    created_paths = []
    for target in TARGET_DIRECTORY_MAP.values():
        path = repo_root / target
        if path.exists():
            continue
        path.mkdir(parents=True, exist_ok=True)
        created_paths.append(str(path.relative_to(repo_root)))

    if created_paths:
        print("created_paths=")
        for item in created_paths:
            print(f"  - {item}")
    else:
        print("created_paths=none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
