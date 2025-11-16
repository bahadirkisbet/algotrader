import asyncio
import signal


def setup_signal_handlers(shutdown_coroutine, logger=None):
    """
    Sets up signal handlers for SIGINT and SIGTERM to trigger the given shutdown_coroutine.

    Args:
        shutdown_coroutine: Coroutine function to be scheduled when a signal is received.
        logger: Optional logger to log signal events.
    """

    def signal_handler(signum, _frame):
        if logger:
            logger.info(f"Received signal {signum}, initiating shutdown...")
        # Schedule the shutdown coroutine using the running event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(shutdown_coroutine())
        else:
            loop.run_until_complete(shutdown_coroutine())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
