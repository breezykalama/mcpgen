from time import sleep


DEFAULT_RETRY_STATUSES = [429, 500, 502, 503, 504]


def retry_enabled(config: dict) -> bool:
    return (config.get("retry") or {}).get("enabled") is True


def max_attempts(config: dict) -> int:
    retry_config = config.get("retry") or {}
    try:
        attempts = int(retry_config.get("max_attempts", 3))
    except (TypeError, ValueError):
        return 1
    return max(1, attempts)


def backoff_seconds(config: dict) -> float:
    retry_config = config.get("retry") or {}
    try:
        return max(0.0, float(retry_config.get("backoff_seconds", 0.5)))
    except (TypeError, ValueError):
        return 0.0


def retry_statuses(config: dict) -> set[int]:
    retry_config = config.get("retry") or {}
    statuses = retry_config.get("retry_statuses", DEFAULT_RETRY_STATUSES)
    result = set()
    for status in statuses:
        try:
            result.add(int(status))
        except (TypeError, ValueError):
            continue
    return result or set(DEFAULT_RETRY_STATUSES)


def should_retry_status(status_code: int, attempt: int, config: dict) -> bool:
    return retry_enabled(config) and attempt < max_attempts(config) and status_code in retry_statuses(config)


def should_retry_network_error(attempt: int, config: dict) -> bool:
    return retry_enabled(config) and attempt < max_attempts(config)


def retry_delay(attempt: int, config: dict) -> float:
    return round(backoff_seconds(config) * attempt, 3)


def sleep_before_retry(attempt: int, config: dict) -> None:
    delay = retry_delay(attempt, config)
    if delay > 0:
        sleep(delay)
