"""In-memory idempotency keys for non-idempotent requests (campaign creation).

A repeated request with the same `Idempotency-Key` gets the stored result instead of
creating a second Keitaro campaign. Keys live in process memory: they are lost on
restart and are not shared between workers, which is fine for this single-process,
single-user tool (see README).
"""

import time
from dataclasses import dataclass, field

from app.core.errors import ConflictError, ValidationFailedError

DEFAULT_TTL_SECONDS = 24 * 60 * 60


@dataclass
class _Entry[T]:
    fingerprint: str
    created_at: float
    # None while the original request is still running.
    result: T | None = None


@dataclass
class IdempotencyStore[T]:
    """Remembers the outcome of a request per key.

    `begin`/`complete`/`abandon` never await, so in asyncio each call is atomic.
    """

    ttl_seconds: float = DEFAULT_TTL_SECONDS
    _entries: dict[str, _Entry[T]] = field(default_factory=dict)

    def begin(self, key: str, fingerprint: str) -> T | None:
        """Claim `key` for a request; returns the stored result if it already succeeded.

        Raises if the same key is still in progress or was used with another request body.
        """
        self._purge_expired()
        entry = self._entries.get(key)
        if entry is None:
            self._entries[key] = _Entry(fingerprint=fingerprint, created_at=time.monotonic())
            return None
        if entry.fingerprint != fingerprint:
            raise ValidationFailedError("Idempotency-Key was already used for a different request")
        if entry.result is None:
            raise ConflictError("This request is already in progress")
        return entry.result

    def complete(self, key: str, result: T) -> None:
        """Store the successful result; repeats of the key will get it back."""
        entry = self._entries.get(key)
        if entry is not None:
            entry.result = result

    def abandon(self, key: str) -> None:
        """Forget a failed request so it can be retried with the same key."""
        self._entries.pop(key, None)

    def _purge_expired(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        expired = [k for k, e in self._entries.items() if e.created_at < cutoff]
        for key in expired:
            del self._entries[key]
