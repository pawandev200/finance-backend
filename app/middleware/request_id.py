"""
Request ID Middleware
──────────────────────
Attaches a unique X-Request-ID to every request/response.
This enables end-to-end tracing across logs — essential in production
when you need to correlate a user's complaint with a specific log line.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Make it available to request handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
