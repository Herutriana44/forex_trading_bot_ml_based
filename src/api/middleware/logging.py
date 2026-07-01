import logging
import json
import time
from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured JSON logging of HTTP requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            process_time = time.time() - start_time
            logger = logging.getLogger(__name__)
            logger.error(
                "request_error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": process_time,
                    "error": str(exc),
                }
            )
            raise

        process_time = time.time() - start_time
        logger = logging.getLogger(__name__)
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": process_time,
            }
        )

        response.headers["X-Request-ID"] = request_id
        return response
