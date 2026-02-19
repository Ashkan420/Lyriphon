import requests
import time
import random

LRCLIB_SEARCH = "https://lrclib.net/api/search"

def get_lyrics(track: str, artist: str, retries: int = 2, timeout: int = 15, delay: float = 2.0):
    attempt = 0
    while attempt <= retries:
        try:
            r = requests.get(
                LRCLIB_SEARCH,
                params={"track_name": track, "artist_name": artist},
                timeout=timeout
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
                #print(f"Retrying in {wait:.1f}s (no lyrics yet)")
                time.sleep(wait)

        except requests.exceptions.RequestException as e:
            attempt += 1
            if attempt <= retries:
                wait = delay * (2 ** attempt) + random.random()
                #print(f"Attempt {attempt-1} failed: {e}, retrying in {wait:.1f}s")
                time.sleep(wait)

    return None
