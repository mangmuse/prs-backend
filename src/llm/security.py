import re
import time
from collections import defaultdict

_KEY_PATTERNS = [
    r"sk-ant-[a-zA-Z0-9\-_]{20,}",
    r"sk-[a-zA-Z0-9\-_]{20,}",
    r"AI[a-zA-Z0-9\-_]{20,}",
]


def sanitize_error_message(message: str) -> str:
    """에러 메시지에서 API Key 패턴을 [REDACTED]로 치환."""
    result = message
    for pattern in _KEY_PATTERNS:
        result = re.sub(pattern, "[REDACTED]", result)
    return result


class InMemoryRateLimiter:
    """Sliding window 기반 in-memory rate limiter."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self._window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self._max_requests:
            return False
        self._requests[key].append(now)
        return True


verify_key_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
