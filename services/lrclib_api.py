import httpx
from services.retry import retry_async

LRCLIB_SEARCH = "https://lrclib.net/api/search"

_client = httpx.AsyncClient(timeout=15.0)


async def get_lyrics(track: str, artist: str, retries: int = 2, delay: float = 2.0):
    async def _fetch():
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
        return None

    return await retry_async(_fetch, retries=retries, delay=delay)
