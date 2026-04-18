import ipaddress
import socket
import urllib.parse

from fastapi import HTTPException


def ensure_public_http_url(raw_url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400, detail="Only public HTTP/HTTPS URLs are allowed"
        )
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL host")

    lowered = parsed.hostname.lower()
    if lowered in {"localhost"} or lowered.endswith(".local"):
        raise HTTPException(
            status_code=400, detail="Local/internal hosts are not allowed"
        )

    try:
        addr_infos = socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=400, detail=f"Unable to resolve host: {exc}"
        ) from exc

    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=400, detail="Internal/private host targets are not allowed"
            )

    return parsed
