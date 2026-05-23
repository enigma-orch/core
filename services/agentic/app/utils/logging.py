"""JSON logging with a per-request correlation id.

Every log record emitted while a request is in flight carries the
request_id assigned by `RequestIdMiddleware`, so logs from agents,
workers, and route handlers can be stitched together. Worker tasks
that aren't tied to a request leave request_id empty.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def current_request_id() -> str:
    return _request_id_ctx.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = current_request_id()
        return True


class _JsonFormatter(logging.Formatter):
    """Single-line JSON per log record. Extras are merged in."""

    _STD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "request_id",
    }

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = getattr(record, "request_id", "")
        if rid:
            payload["request_id"] = rid
        # Merge any extra=... attributes the caller passed in.
        for k, v in record.__dict__.items():
            if k in self._STD_ATTRS or k.startswith("_"):
                continue
            payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON handler + request-id filter at the root logger.

    Idempotent so it can be called from main.py and from tests without
    duplicating handlers.
    """
    root = logging.getLogger()
    # Drop pre-existing handlers (basicConfig may have run already).
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet a few chatty libraries — they still log at WARNING+.
    for noisy in ("httpx", "httpcore", "boto3", "botocore", "s3transfer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request_id per incoming HTTP request and echoes it back.

    Reuses an inbound X-Request-Id if the caller already chose one (e.g.
    a frontend ingress), otherwise mints a fresh UUID4. The id is bound
    into a ContextVar so any log call inside the request flow picks it up.
    """

    HEADER = "x-request-id"

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(self.HEADER) or uuid.uuid4().hex
        token = _request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[self.HEADER] = rid
        return response
