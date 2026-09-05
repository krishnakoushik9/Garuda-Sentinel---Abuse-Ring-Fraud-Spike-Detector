"""Utility helpers for Cognee Cloud Integration."""

import time
import math
import logging

logger = logging.getLogger("cognee.utils")

def mask_api_key(key: str) -> str:
    """Masks an API key for safe logging, exposing only the first few characters.
    
    Example: cognee_key_12345 -> cog_*********
    """
    if not key:
        return "None"
    if len(key) <= 6:
        return "***"
    return f"{key[:4]}***{key[-4:] if len(key) >= 12 else ''}"


def calculate_backoff(retry_count: int, factor: float = 1.5, max_delay: float = 10.0) -> float:
    """Calculates exponential backoff delay with jitter.
    
    Formula: min(max_delay, factor * (2 ** retry_count)) + jitter
    """
    import random
    delay = min(max_delay, factor * math.pow(2, retry_count))
    jitter = random.uniform(0.1, 0.5)
    return delay + jitter


class LatencyTimer:
    """Context manager for measuring request elapsed time in milliseconds."""
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    @property
    def elapsed_ms(self) -> float:
        end_time = getattr(self, "end", None) or time.perf_counter()
        return (end_time - self.start) * 1000.0

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.perf_counter()
