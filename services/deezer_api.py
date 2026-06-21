"""Deezer API client — search tracks, fetch track/album metadata."""

import httpx
import logging

logger = logging.getLogger(__name__)

# --- API endpoints ---

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
DEEZER_TRACK_URL = "https://api.deezer.com/track/"
DEEZER_ALBUM_URL = "https://api.deezer.com/album/"

_client = httpx.AsyncClient(timeout=10.0)


async def search_tracks(query: str, limit: int = 25):
    """Search Deezer for tracks matching *query*. Returns a list of track dicts, or None on error."""
    try:
        r = await _client.get(DEEZER_SEARCH_URL, params={"q": query})
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])[:limit]
    except httpx.TimeoutException:
        logger.warning("Deezer search timed out for query: %s", query)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("Deezer search HTTP %s for query: %s", e.response.status_code, query)
        return None
    except Exception:
        logger.exception("Deezer search failed for query: %s", query)
        return None


async def get_track(track_id: int):
    """Fetch full track details from Deezer by *track_id*."""
    try:
        r = await _client.get(DEEZER_TRACK_URL + str(track_id))
        r.raise_for_status()
        return r.json()
    except httpx.TimeoutException:
        logger.warning("Deezer get_track timed out for track_id: %s", track_id)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("Deezer get_track HTTP %s for track_id: %s", e.response.status_code, track_id)
        return None
    except Exception:
        logger.exception("Deezer get_track failed for track_id: %s", track_id)
        return None


async def get_album(album_id: int):
    """Fetch album details (including release date) from Deezer by *album_id*."""
    try:
        r = await _client.get(DEEZER_ALBUM_URL + str(album_id))
        r.raise_for_status()
        return r.json()
    except httpx.TimeoutException:
        logger.warning("Deezer get_album timed out for album_id: %s", album_id)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("Deezer get_album HTTP %s for album_id: %s", e.response.status_code, album_id)
        return None
    except Exception:
        logger.exception("Deezer get_album failed for album_id: %s", album_id)
        return None
