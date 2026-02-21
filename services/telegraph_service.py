import re

from telegraph import Telegraph
from config import TELEGRAPH_ACCESS_TOKEN, CHANNEL_LINK, DEEZLOAD_BOT

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
    track_link = f"{DEEZLOAD_BOT}deezerttrack{track_id}"
    artist_link = f"{DEEZLOAD_BOT}deezertartist{artist_id}"
    album_link = f"{DEEZLOAD_BOT}deezertalbum{album_id}"

    if not lyrics:
        lyrics = "Lyrics not found."

    # Escape HTML special chars to prevent broken pages
    #lyrics = lyrics.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


    import html

    # Escape HTML
    lyrics = html.escape(lyrics)

    # Normalize newlines first (if coming as \n)
    lyrics = lyrics.replace("\r\n", "\n").replace("\r", "\n")
    lyrics = lyrics.replace("\n", "<br>")

    # Normalize 2+ breaks into exactly two
    lyrics = re.sub(r'(<br>\s*){2,}', '<br><br>', lyrics)

    segments = lyrics.split("<br><br>")

    html_parts = []

    for i, segment in enumerate(segments):
        segment = segment.strip()
        if not segment:
            continue

        lines = [line.strip() for line in segment.split("<br>") if line.strip()]

        for line in lines:
            html_parts.append(f"<p>{line}</p>")

        # Add double break between segments (except last)
        if i < len(segments) - 1:
            html_parts.append("<p>&#8203;</p>")

    html_lyrics = "\n".join(html_parts)


    html_content = f"""
    <img src="{album_cover_url}">
    <br>

    <p>🎧 Track: <a href="{track_link}">{track}</a></p>
    <p>👤 Artist: <a href="{artist_link}">{artist}</a></p>
    <p>💽 Album: <a href="{album_link}">{album}</a></p>
    <p>📅 Date: {release_date}</p>

    <hr>
    <h3>Lyrics</h3>
    {html_lyrics}
    """

    print("\n" + "="*40)
    print("TELEGRAPH HTML CONTENT:")
    print("="*40)
    print(html_content)
    print("="*40 + "\n")


    response = telegraph.create_page(
        title=track,
        author_name=author_name,
        author_url=CHANNEL_LINK,  # always your channel
        html_content=html_content
    )

    return "https://telegra.ph/" + response["path"]
