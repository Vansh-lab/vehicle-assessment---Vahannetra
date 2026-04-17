import json
import os
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _read_secret_from_file(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as file:
            value = file.read().strip()
            return value or None
    except OSError:
        return None


def _vault_lookup(secret_name: str) -> str | None:
    vault_addr = os.getenv("VAHANNETRA_VAULT_ADDR")
    vault_token = os.getenv("VAHANNETRA_VAULT_TOKEN")
    vault_path = os.getenv("VAHANNETRA_VAULT_PATH", "secret/data/vahannetra")
    if not vault_addr or not vault_token:
        return None
    if not vault_addr.startswith("https://"):
        return None

    request = Request(
        f"{vault_addr.rstrip('/')}/v1/{vault_path.lstrip('/')}",
        headers={"X-Vault-Token": vault_token},
    )
    try:
        with urlopen(request, timeout=4) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError):
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    nested = data.get("data") if isinstance(data.get("data"), dict) else data
    value = nested.get(secret_name) if isinstance(nested, dict) else None
    return str(value) if value is not None else None


@lru_cache(maxsize=128)
def get_secret(secret_name: str, default: str | None = None) -> str | None:
    value = os.getenv(secret_name)
    if value:
        return value

    file_hint = os.getenv(f"{secret_name}_FILE")
    if file_hint:
        file_value = _read_secret_from_file(file_hint)
        if file_value:
            return file_value

    vault_value = _vault_lookup(secret_name)
    if vault_value:
        return vault_value

    return default
