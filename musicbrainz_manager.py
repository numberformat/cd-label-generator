import musicbrainzngs as mb
import discid
import time
import random
import urllib.error
import re

def init_musicbrainz(app_name="CDLabeler", version="1.0", contact="you@example.com"):
    mb.set_useragent(app_name, version, contact)

def extract_mbid_from_text(text):
    if not text:
        return None

    match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        text
    )
    if match:
        return match.group(0)

    return None


def mb_with_retry(func, *args, retries=5, base_delay=1.0, **kwargs):
    response_error = getattr(mb, "ResponseError", None)
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if (
                response_error
                and isinstance(e, response_error)
                and getattr(e, "status", None) == 404
            ) or (isinstance(e, urllib.error.HTTPError) and e.code == 404):
                raise
            attempt += 1
            if attempt > retries:
                print(f"MusicBrainz failed after {retries} retries: {e}")
                raise

            delay = base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, 0.5)
            print(f"MusicBrainz error: {e} - retrying in {delay:.1f}s (attempt {attempt}/{retries})")
            time.sleep(delay)

def get_release_by_mbid(mbid, print_func=print):
    try:
        result = mb_with_retry(mb.get_release_by_id, mbid, includes=["recordings", "artists"])
        release = result["release"]

        artist = ""

        if "artist-credit" in release and release["artist-credit"]:
            ac = release["artist-credit"][0]
            if isinstance(ac, dict) and "artist" in ac:
                artist = ac["artist"].get("name", "")
            elif isinstance(ac, dict) and "name" in ac:
                artist = ac.get("name", "")
        elif "artist-credit-phrase" in release:
            artist = release.get("artist-credit-phrase", "")

        album = release.get("title", "")
        date = release.get("date", "")
        year = date[:4] if date else ""
        mbid = release.get("id", mbid)

        return artist, album, year, mbid

    except Exception as e:
        print_func(f"Failed to fetch release for MBID {mbid}: {e}")
        return None, None, None, None

def get_musicbrainz_metadata(drive):
    try:
        disc = discid.read(drive)

        result = mb_with_retry(
            mb.get_releases_by_discid,
            disc.id,
            includes=["artists", "release-groups"]
        )

        release = result["disc"]["release-list"][0]

        artist = release["artist-credit"][0]["artist"]["name"]
        album = release["title"]
        year = release.get("date", "")[:4]
        mbid = release["id"]

        return artist, album, year, mbid

    except Exception:
        return None, None, None, None
    

# ---------- SEARCH / FALLBACK HELPERS ----------

def search_mb_by_artist_album(artist, album):
    try:
        result = mb_with_retry(
            mb.search_releases,
            query=f'artist:"{artist}" AND release:"{album}"',
            limit=10
        )
        releases = result.get("release-list", [])
    except Exception:
        return None, None, None, None

    if not releases:
        return None, None, None, None

    r = releases[0]
    return (
        r.get("artist-credit", [{}])[0].get("artist", {}).get("name", ""),
        r.get("title", ""),
        r.get("date", "")[:4],
        r.get("id")
    )
