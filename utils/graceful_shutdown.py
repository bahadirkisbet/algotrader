import asyncio
from typing import Awaitable, Callable, List, Optional

_shutdown_callbacks: List[Callable[[], Awaitable[None]]] = []
_shutdown_lock = asyncio.Lock()
_shutdown_started = False


def register_shutdown_callback(callback: Callable[[], Awaitable[None]]) -> None:
    """
    Registers a coroutine callback to be executed during graceful shutdown.
    """
    _shutdown_callbacks.append(callback)


async def shutdown_all_services(logger: Optional[object] = None):
    """
    Run all registered shutdown callbacks concurrently.
    This guarantees each service is given a chance to cleanup.
    """
    global _shutdown_started
    async with _shutdown_lock:
        if _shutdown_started:
            if logger:
                logger.warning("Shutdown already in progress, skipping duplicate call.")
            return
        _shutdown_started = True

        if logger:
            logger.info("Running graceful shutdown for all registered services...")

        if not _shutdown_callbacks:
            if logger:
                logger.info("No shutdown callbacks registered.")
            return

        tasks = []
        for cb in _shutdown_callbacks:
            tasks.append(asyncio.create_task(_safe_run_callback(cb, logger)))
        await asyncio.gather(*tasks)

        if logger:
            logger.info("All shutdown callbacks completed.")


async def _safe_run_callback(
    cb: Callable[[], Awaitable[None]], logger: Optional[object] = None
):
    """
    Run a shutdown callback and catch/log all exceptions.
    """
    try:
        await cb()
    except Exception as e:
        if logger:
            logger.error(f"Exception during shutdown callback: {e}")


def clear_shutdown_callbacks():
    """
    For testing: remove all registered shutdown callbacks.
    """
    _shutdown_callbacks.clear()
