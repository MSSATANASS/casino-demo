import hashlib
import threading
import time


class RateLimiter:
    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _key(self, *parts: str) -> str:
        return hashlib.sha256(":".join(parts).encode()).hexdigest()

    def allowed(self, *parts: str) -> bool:
        key = self._key(*parts)
        now = time.monotonic()
        with self._lock:
            ts = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(ts) >= self.limit:
                self._hits[key] = ts
                return False
            ts.append(now)
            self._hits[key] = ts
            return True

    def reset(self):
        with self._lock:
            self._hits.clear()


def client_ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"