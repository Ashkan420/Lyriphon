import httpx
import asyncio
import random
import logging

logger = logging.getLogger(__name__)

LRCLIB_SEARCH = "https://lrclib.net/api/search"

_client = httpx.AsyncClient(timeout=15.0)


async def get_lyrics(track: str, artist: str, retries: int = 2, delay: float = 2.0):
    attempt = 0
    while attempt <= retries:
        try:
            r = await _client.get(
                LRCLIB_SEARCH,
                params={"track_name": track, "artist_name": artist},
            )
            r.raise_for_status()
            results = r.json()

            if results:
                best = results[0]
                lyrics = best.get("plainLyrics") or best.get("syncedLyrics")
                if lyrics:
                    return lyrics

            attempt += 1
            if attempt <= retries:
                logger.debug(
                    "No lyrics found for '%s' by '%s', retrying (%d/%d)",
                    track, artist, attempt, retries,
                )
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)

        except httpx.TimeoutException:
            attempt += 1
            logger.warning(
                "LRCLIB timed out for '%s' by '%s' (attempt %d/%d)",
                track, artist, attempt, retries + 1,
            )
            if attempt <= retries:
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)
        except httpx.HTTPStatusError as e:
            attempt += 1
            logger.warning(
                "LRCLIB HTTP %s for '%s' by '%s' (attempt %d/%d)",
                e.response.status_code, track, artist, attempt, retries + 1,
            )
            if attempt <= retries:
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)
        except Exception:
            attempt += 1
            logger.exception(
                "LRCLIB request failed for '%s' by '%s' (attempt %d/%d)",
                track, artist, attempt, retries + 1,
            )
            if attempt <= retries:
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)

    logger.info("No lyrics found for '%s' by '%s' after %d attempts", track, artist, retries + 1)
    return None
