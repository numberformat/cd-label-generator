import discogs_client
import os
from dotenv import load_dotenv

_DISCOGS_TOKEN = None


def get_discogs_token():
    global _DISCOGS_TOKEN
    if _DISCOGS_TOKEN:
        return _DISCOGS_TOKEN

    load_dotenv()

    token = os.getenv("DISCOGS_TOKEN")
    if token:
        _DISCOGS_TOKEN = token
        return _DISCOGS_TOKEN

    print("\nDiscogs token not found.")
    print("Create one at: https://www.discogs.com/settings/developers\n")
    token = input("Enter your Discogs user token: ").strip()

    with open(".env", "a", encoding="utf-8") as f:
        f.write(f"\nDISCOGS_TOKEN={token}\n")

    print("Saved token to .env\n")
    _DISCOGS_TOKEN = token
    return _DISCOGS_TOKEN

def get_discogs_genre(artist, album, token=None):
    token = token or get_discogs_token()
    d = discogs_client.Client("CDLabeler/1.0", user_token=token)

    try:
        results = d.search(artist=artist, release_title=album, type="release")
    except Exception:
        return ""

    if results:
        r = results[0]
        if r.genres:
            return r.genres[0]

    return ""

def search_discogs_by_artist_album(artist, album, token=None):
    token = token or get_discogs_token()
    d = discogs_client.Client("CDLabeler/1.0", user_token=token)

    try:
        results = d.search(artist=artist, release_title=album, type="release")
    except Exception:
        return None, None, None, None

    if results:
        r = results[0]
        return (
            r.artists[0].name if r.artists else "",
            r.title,
            str(r.year) if r.year else "",
            r.genres[0] if r.genres else "",
        )

    return None, None, None, None
