from __future__ import annotations

import logging
from typing import Any, Callable


logger = logging.getLogger(__name__)


def run_guarded_background_task(task_name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    try:
        logger.info("Background task started: %s", task_name)
        fn(*args, **kwargs)
        logger.info("Background task finished: %s", task_name)
    except Exception:
        logger.exception("Background task failed: %s", task_name)
