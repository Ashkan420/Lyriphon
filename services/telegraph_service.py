from telegraph import Telegraph
from config import TELEGRAPH_ACCESS_TOKEN, CHANNEL_LINK, DEEZLOAD_BOT
from services.lyrics_formatter import format_lyrics_for_telegraph

telegraph = Telegraph(access_token=TELEGRAPH_ACCESS_TOKEN)


def create_song_telegraph(
    author_name: str,
    track: str,
    track_id: int,
    artist: str,
    artist_id: int,
    album: str,
    album_id: int,
    album_cover_url: str,
    release_date: str,
    lyrics: str
):
    """
    Create a Telegraph page for a song and return the URL and path.
    """
    track_link = f"{DEEZLOAD_BOT}deezerttrack{track_id}"
    artist_link = f"{DEEZLOAD_BOT}deezertartist{artist_id}"
    album_link = f"{DEEZLOAD_BOT}deezertalbum{album_id}"

    formatted_lyrics = format_lyrics_for_telegraph(lyrics)

    html_content = _build_html_page(
        track,
        artist,
        album,
        release_date,
        album_cover_url,
        track_link,
        artist_link,
        album_link,
        formatted_lyrics
    )

    #_debug_print(html_content)

    response = telegraph.create_page(
        title=track,
        author_name=author_name,
        author_url=CHANNEL_LINK,
        html_content=html_content
    )

    url = "https://telegra.ph/" + response["path"]
    path = response["path"]
    
    last_data = {
        "author_name": author_name,
        "track": track,
        "track_link": track_link,
        "artist": artist,
        "artist_link": artist_link,
        "album": album,
        "album_link": album_link,
        "album_cover_url": album_cover_url,
        "release_date": release_date,
        "path": path
    }

    return url, path, last_data


def edit_song_page(last_data: dict, lyrics: str):

    formatted_lyrics = format_lyrics_for_telegraph(lyrics)

    html_content = _build_html_page(
        track=last_data["track"],
        artist=last_data["artist"],
        album=last_data["album"],
        release_date=last_data["release_date"],
        album_cover_url=last_data["album_cover_url"],
        track_link=last_data["track_link"],
        artist_link=last_data["artist_link"],
        album_link=last_data["album_link"],
        formatted_lyrics=formatted_lyrics
    )

    telegraph.edit_page(
        path=last_data["path"],
        title=last_data["track"],
        html_content=html_content,
        author_name=last_data["author_name"],
        author_url=CHANNEL_LINK
    )


def _build_html_page(
    track,
    artist,
    album,
    release_date,
    album_cover_url,
    track_link,
    artist_link,
    album_link,
    formatted_lyrics
):
    return f"""
<img src="{album_cover_url}">
<br>

<p><strong>🎧 Track:</strong> <a href="{track_link}">{track}</a></p>
<p><strong>👤 Artist:</strong> <a href="{artist_link}">{artist}</a></p>
<p><strong>💽 Album:</strong> <a href="{album_link}">{album}</a></p>
<p><strong>📅 Date:</strong> {release_date}</p>

<hr>
<h3>Lyrics</h3>

{formatted_lyrics}
"""


def _debug_print(html_content: str):
    print("\n" + "=" * 40)
    print("TELEGRAPH HTML CONTENT:")
    print("=" * 40)
    print(html_content)
    print("=" * 40 + "\n")
