import json
import logging
import time
from contextvars import ContextVar
from typing import Any

# ContextVar to store correlation IDs for log tracing
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", None),
            "path": f"{record.pathname}:{record.lineno}",
        }

        # Include raw dict properties passed via extra
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_payload.update(record.extra_data)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


class CustomLogger(logging.Logger):
    """Logger subclass that intercepts extra_data kwargs and converts them to standard extra dictionary."""
    def _log(self, level: int, msg: Any, args: Any, **kwargs: Any) -> None:
        extra_data = kwargs.pop("extra_data", None)
        if extra_data is not None:
            extra = kwargs.setdefault("extra", {})
            extra["extra_data"] = extra_data
        super()._log(level, msg, args, **kwargs)


# Register custom logger class
logging.setLoggerClass(CustomLogger)


def setup_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clean existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler with JSON Formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    console_handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(console_handler)

    # Disable generic uvicorn formatting to avoid duplicates/unstructured stdout
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("uvicorn.access").addHandler(console_handler)
    logging.getLogger("uvicorn.error").addHandler(console_handler)


# Shared Logger Instances
logger = logging.getLogger("app.core")
workflow_logger = logging.getLogger("app.workflow")
performance_logger = logging.getLogger("app.performance")
security_logger = logging.getLogger("app.security")
