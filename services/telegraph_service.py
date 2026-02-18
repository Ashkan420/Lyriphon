from telegraph import Telegraph
from config import TELEGRAPH_ACCESS_TOKEN, CHANNEL_LINK, DEEZLOAD_BOT

telegraph = Telegraph(access_token=TELEGRAPH_ACCESS_TOKEN)


def create_song_telegraph(
    author_name: str,
    author_url: str,
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

    content = [
        {
            "tag": "a",
            "attrs": {"href": CHANNEL_LINK},
            "children": [
                {"tag": "img", "attrs": {"src": album_cover_url}}
            ]
        },

        {"tag": "p", "children": [
            "🎧 Track: ",
            {"tag": "a", "attrs": {"href": track_link}, "children": [track]}
        ]},

        {"tag": "p", "children": [
            "👤 Artist: ",
            {"tag": "a", "attrs": {"href": artist_link}, "children": [artist]}
        ]},

        {"tag": "p", "children": [
            "💽 Album: ",
            {"tag": "a", "attrs": {"href": album_link}, "children": [album]}
        ]},

        {"tag": "p", "children": [f"📅 Date: {release_date}"]},

        {"tag": "hr"},

        {"tag": "h3", "children": ["Lyrics"]},
        {"tag": "pre", "children": [lyrics]}
    ]

    response = telegraph.create_page(
        title=track,
        author_name=author_name,
        author_url=author_url,
        html_content=None,
        content=content
    )

    return "https://telegra.ph/" + response["path"]
