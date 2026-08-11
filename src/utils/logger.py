import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict


class StructuredLogger:
    """JSON/Formatted Structured Logger for pipeline observability."""
    
    def __init__(self, name: str = "AIPipeline"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive keys like API tokens before logging."""
        sanitized = {}
        for k, v in data.items():
            if any(secret in k.lower() for secret in ["key", "token", "secret", "auth", "password"]):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized

    def info(self, msg: str, **kwargs):
        if kwargs:
            meta = self._sanitize(kwargs)
            self.logger.info(f"{msg} | {json.dumps(meta)}")
        else:
            self.logger.info(msg)

    def warning(self, msg: str, **kwargs):
        if kwargs:
            meta = self._sanitize(kwargs)
            self.logger.warning(f"{msg} | {json.dumps(meta)}")
        else:
            self.logger.warning(msg)

    def error(self, msg: str, **kwargs):
        if kwargs:
            meta = self._sanitize(kwargs)
            self.logger.error(f"{msg} | {json.dumps(meta)}")
        else:
            self.logger.error(msg)

    def debug(self, msg: str, **kwargs):
        if kwargs:
            meta = self._sanitize(kwargs)
            self.logger.debug(f"{msg} | {json.dumps(meta)}")
        else:
            self.logger.debug(msg)


logger = StructuredLogger()
