from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable, Iterable, Tuple, TypeVar

from app.core.errors import ExternalServiceError


logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_with_timeout(
    func: Callable[..., T],
    *args: Any,
    timeout_seconds: float,
    timeout_message: str,
    **kwargs: Any,
) -> T:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ExternalServiceError(
                timeout_message,
                code="operation_timeout",
                status_code=504,
                details={"timeout_seconds": timeout_seconds},
            ) from exc


def retry_call(
    func: Callable[..., T],
    *args: Any,
    attempts: int,
    retry_exceptions: Tuple[type[BaseException], ...],
    operation_name: str,
    base_delay_seconds: float = 0.5,
    **kwargs: Any,
) -> T:
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            if attempt > 1:
                logger.warning("%s retry attempt %s/%s", operation_name, attempt, attempts)
            return func(*args, **kwargs)
        except retry_exceptions as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(base_delay_seconds * (2 ** (attempt - 1)))

    assert last_error is not None
    raise last_error
