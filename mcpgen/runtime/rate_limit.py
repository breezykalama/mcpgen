import time
from collections import defaultdict, deque
from math import ceil


_GLOBAL_HITS = deque()
_TOOL_HITS = defaultdict(deque)


def check_rate_limit(tool_name: str | None, config: dict) -> dict:
    """Check in-memory global and per-tool rate limits."""
    rate_config = config.get("rate_limit") or {}
    if rate_config.get("enabled") is not True:
        return allowed_decision()

    now = time.time()
    window_seconds = int(rate_config.get("window_seconds", 60))
    global_limit = int(rate_config.get("global", 100))
    per_tool_limit = int(rate_config.get("per_tool", 10))

    prune_hits(_GLOBAL_HITS, now, window_seconds)
    if len(_GLOBAL_HITS) >= global_limit:
        return blocked_decision("global", retry_after(_GLOBAL_HITS, now, window_seconds))

    if tool_name is not None:
        tool_hits = _TOOL_HITS[tool_name]
        prune_hits(tool_hits, now, window_seconds)
        if len(tool_hits) >= per_tool_limit:
            return blocked_decision("per_tool", retry_after(tool_hits, now, window_seconds))

    return allowed_decision()


def record_rate_limit_hit(tool_name: str | None, config: dict) -> None:
    """Record an accepted operational request."""
    rate_config = config.get("rate_limit") or {}
    if rate_config.get("enabled") is not True:
        return

    now = time.time()
    _GLOBAL_HITS.append(now)
    if tool_name is not None:
        _TOOL_HITS[tool_name].append(now)


def reset_rate_limits() -> None:
    _GLOBAL_HITS.clear()
    _TOOL_HITS.clear()


def prune_hits(hits: deque, now: float, window_seconds: int) -> None:
    cutoff = now - window_seconds
    while hits and hits[0] <= cutoff:
        hits.popleft()


def retry_after(hits: deque, now: float, window_seconds: int) -> int:
    if not hits:
        return 0
    return max(1, ceil(window_seconds - (now - hits[0])))


def allowed_decision() -> dict:
    return {
        "allowed": True,
        "scope": None,
        "retry_after": 0,
        "reason": "",
    }


def blocked_decision(scope: str, retry_after_seconds: int) -> dict:
    return {
        "allowed": False,
        "scope": scope,
        "retry_after": retry_after_seconds,
        "reason": "rate limit exceeded",
    }
