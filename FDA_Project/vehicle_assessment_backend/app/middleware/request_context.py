from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response


async def request_context_middleware(request: Request, call_next: Callable) -> Response:
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    return response
