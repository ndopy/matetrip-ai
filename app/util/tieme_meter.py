import logging
import time

logger = logging.getLogger(__name__)


def timeMeter(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f"[time] {func.__name__} took {(end-start)*1000:.2f} ms")
        return result

    return wrapper
