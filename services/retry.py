import time
import random
import asyncio


def retry_sync(fn, retries=2, delay=2.0):
    """Call *fn()* with exponential-backoff retries. Re-raises on final failure."""
    attempt = 0
    while attempt <= retries:
        try:
            return fn()
        except Exception:
            attempt += 1
            if attempt <= retries:
                time.sleep(delay * (2 ** attempt) + random.random())
            else:
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
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)
    return None
