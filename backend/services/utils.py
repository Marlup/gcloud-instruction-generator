from functools import wraps
from time import perf_counter
import logging

logger = logging.getLogger(__name__)

def get_duration(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            duration = perf_counter() - start
            logging.info(f"Duration: {duration:.6f}s for '{func.__name__}'")
    return wrapper
