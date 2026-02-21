import requests

DEEZEER_SEARCH_URL = "https://api.deezer.com/search"
DEEZEER_TRACK_URL = "https://api.deezer.com/track/"
DEEZEER_ALBUM_URL = "https://api.deezer.com/album/"

def search_tracks(query: str, limit: int = 25):
    r = requests.get(DEEZEER_SEARCH_URL, params={"q": query})
    data = r.json()

    results = data.get("data", [])[:limit]
    return results


def get_track(track_id: int):
    r = requests.get(DEEZEER_TRACK_URL + str(track_id))
    return r.json()


def get_album(album_id: int):
    r = requests.get(DEEZEER_ALBUM_URL + str(album_id))
    return r.json()
