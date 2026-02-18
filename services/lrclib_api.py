import requests

LRCLIB_SEARCH = "https://lrclib.net/api/search"

def get_lyrics(track: str, artist: str):
    try:
        r = requests.get(LRCLIB_SEARCH, params={
            "track_name": track,
            "artist_name": artist
        })

        results = r.json()

        if not results:
            return None

        # Best match = first result
        best = results[0]

        # LRCLIB usually returns either "syncedLyrics" or "plainLyrics"
        lyrics = best.get("plainLyrics") or best.get("syncedLyrics")

        return lyrics

    except Exception:
        return None
