"""Synchronous and async retry helpers with exponential backoff."""

import time
import random
import asyncio
import logging

logger = logging.getLogger(__name__)


def retry_sync(fn, retries=2, delay=2.0):
    """Call *fn()* with exponential-backoff retries. Re-raises on final failure."""
    attempt = 0
    while attempt <= retries:
        try:
            return fn()
        except Exception:
            attempt += 1
            if attempt <= retries:
                logger.warning("retry_sync attempt %d/%d failed", attempt, retries + 1)
                time.sleep(delay * (2 ** attempt) + random.random())
            else:
                logger.exception("retry_sync failed after %d attempts", retries + 1)
                raise


async def retry_async(fn, retries=2, delay=2.0):
    """Await *fn()* with exponential-backoff retries. Returns None on final failure."""
    attempt = 0
    while attempt <= retries:
        try:
            return await fn()
        except Exception:
            attempt += 1
            if attempt <= retries:
                logger.warning("retry_async attempt %d/%d failed", attempt, retries + 1)
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)
            else:
                logger.exception("retry_async failed after %d attempts", retries + 1)
    return None
