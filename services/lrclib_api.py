import requests
import time

LRCLIB_SEARCH = "https://lrclib.net/api/search"

def get_lyrics(track: str, artist: str, retries: int = 2, delay: float = 1.0):
    """
    Fetch lyrics from LRCLIB with a few retries if the first attempt fails.
    - retries: number of extra attempts if result is empty or request fails
    - delay: seconds to wait between retries
    """
    attempt = 0
    while attempt <= retries:
        try:
            r = requests.get(LRCLIB_SEARCH, params={
                "track_name": track,
                "artist_name": artist
            }, timeout=5)  # avoid hanging

            r.raise_for_status()
            results = r.json()

            if results:
                best = results[0]
                lyrics = best.get("plainLyrics") or best.get("syncedLyrics")
                if lyrics:  # only return if we actually got some lyrics
                    return lyrics

            # If no results or empty lyrics, retry
            attempt += 1
            if attempt <= retries:
                time.sleep(delay)

        except Exception:
            attempt += 1
            if attempt <= retries:
                time.sleep(delay)

    # Failed after retries
    return None
