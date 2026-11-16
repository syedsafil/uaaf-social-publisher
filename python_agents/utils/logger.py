"""
UAAF Logger — Structured logging with timestamps and emoji prefixes.
Windows-safe UTF-8 encoding.
"""
import sys
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Logger:
    def __init__(self):
        self.prefix = "[UAAF]"

    def _format(self, level: str, msg: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        return f"{ts} {self.prefix} {level} {msg}"

    def info(self, msg: str):
        print(self._format("ℹ️", msg), flush=True)

    def warn(self, msg: str):
        print(self._format("⚠️", msg), flush=True)

    def error(self, msg: str):
        print(self._format("❌", msg), file=sys.stderr, flush=True)

    def success(self, msg: str):
        print(self._format("✅", msg), flush=True)


log = Logger()

