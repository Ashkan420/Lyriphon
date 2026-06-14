import httpx

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
DEEZER_TRACK_URL = "https://api.deezer.com/track/"
DEEZER_ALBUM_URL = "https://api.deezer.com/album/"

_client = httpx.AsyncClient(timeout=10.0)


async def search_tracks(query: str, limit: int = 25):
    try:
        r = await _client.get(DEEZER_SEARCH_URL, params={"q": query})
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])[:limit]
    except Exception:
        return None


async def get_track(track_id: int):
    try:
        r = await _client.get(DEEZER_TRACK_URL + str(track_id))
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def get_album(album_id: int):
    try:
        r = await _client.get(DEEZER_ALBUM_URL + str(album_id))
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
