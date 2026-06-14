import httpx
import asyncio
import random

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
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)

        except Exception:
            attempt += 1
            if attempt <= retries:
                wait = delay * (2 ** attempt) + random.random()
                await asyncio.sleep(wait)

    return None
