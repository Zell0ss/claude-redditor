"""Configure stdlib logging to also write JSON to a LogCentral-compatible file."""
import json
import logging
import os
from datetime import timezone
from pathlib import Path


class LogCentralHandler(logging.Handler):
    """Write stdlib log records as JSON to a LogCentral-compatible file."""

    def __init__(self, log_file: Path):
        super().__init__()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = log_file

    def emit(self, record: logging.LogRecord) -> None:
        try:
            from datetime import datetime
            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                )[:-3] + "Z",
                "level": record.levelname,
                "source": "clauderedditor",
                "message": self.format(record),
                "module": record.module,
            }
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            self.handleError(record)


def setup_logcentral(log_dir: Path | None = None) -> None:
    """Add LogCentral JSON handler to root logger."""
    resolved_dir = Path(log_dir or os.getenv("LOGCENTRAL_LOG_DIR", "logs"))
    log_file = resolved_dir / "clauderedditor.log"

    handler = LogCentralHandler(log_file)
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    # Avoid duplicate handlers if called twice
    if not any(isinstance(h, LogCentralHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)
        # Ensure root logger level allows INFO through
        if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
            root_logger.setLevel(logging.INFO)
