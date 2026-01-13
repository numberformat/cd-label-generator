import discid
import musicbrainzngs as mb
import discogs_client
import pandas as pd
from pathlib import Path
import time
import ctypes
import os
from dotenv import load_dotenv
import string
import win32file
import win32con
import win32clipboard
import re
import random

# ---------------- CONFIG ----------------
CSV_PATH = "data/cd_labels.csv"
# ---------------------------------------

mb.set_useragent("CDLabeler", "1.0", "you@example.com")

# ---------- ENV / TOKEN HANDLING ----------

def get_discogs_token():
    load_dotenv()

    token = os.getenv("DISCOGS_TOKEN")
    if token:
        return token

    print("\nDiscogs token not found.")
    print("Create one at: https://www.discogs.com/settings/developers\n")
    token = input("Enter your Discogs user token: ").strip()

    with open(".env", "a", encoding="utf-8") as f:
        f.write(f"\nDISCOGS_TOKEN={token}\n")

    print("Saved token to .env\n")
    return token


DISCOGS_TOKEN = get_discogs_token()

# ---------- RETRY WRAPPER ----------

def mb_with_retry(func, *args, retries=5, base_delay=1.0, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt > retries:
                print(f"MusicBrainz failed after {retries} retries: {e}")
                raise

            delay = base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, 0.5)
            print(f"MusicBrainz error: {e} — retrying in {delay:.1f}s (attempt {attempt}/{retries})")
            time.sleep(delay)

# ---------- DRIVE DETECTION ----------

def get_optical_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()

    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive = f"{letter}:"
            try:
                drive_type = win32file.GetDriveType(drive)
                if drive_type == win32con.DRIVE_CDROM:
                    drives.append(drive)
            except:
                pass
        bitmask >>= 1

    return drives


DRIVES = get_optical_drives()

if not DRIVES:
    print("No optical drives found. Exiting.")
    exit(1)

print(f"Detected optical drives: {', '.join(DRIVES)}")

# ---------- CORE FUNCTIONS ----------

def eject_cd(drive_letter):
    drive = drive_letter.rstrip(":")
    cmd = f"open {drive}: type CDAudio alias drive"
    ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)
    ctypes.windll.winmm.mciSendStringW("set drive door open", None, 0, None)
    ctypes.windll.winmm.mciSendStringW("close drive", None, 0, None)


def get_current_disc_id(drive):
    try:
        disc = discid.read(drive)
        return disc.id
    except:
        return None


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


def get_discogs_genre(artist, album):
    d = discogs_client.Client("CDLabeler/1.0", user_token=DISCOGS_TOKEN)

    try:
        results = d.search(artist=artist, release_title=album, type="release")
    except Exception:
        return ""

    if results:
        r = results[0]
        if r.genres:
            return r.genres[0]

    return ""


def clean_year(y):
    try:
        return str(int(float(y)))
    except:
        return ""


def append_to_csv(row):
    csv_path = Path(CSV_PATH)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(csv_path, index=False)

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


def search_discogs_by_artist_album(artist, album):
    d = discogs_client.Client("CDLabeler/1.0", user_token=DISCOGS_TOKEN)

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


def prompt_for_artist_album():
    print("\nMetadata not found. Please enter artist and album to search.")
    artist = input("Artist: ").strip()
    album = input("Album: ").strip()
    if not artist or not album:
        return None, None
    return artist, album


def get_clipboard_text():
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return data.strip()
    except:
        return None


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


def prompt_for_mbid_with_clipboard():
    print("\nManual identification required.")
    print("Search on MusicBrainz by:")
    print("  - Artist name")
    print("  - Album title")
    print("  - Track count + durations")
    print("\nOpen the correct release page and copy the URL.")
    print("Press Enter to use the MBID from your clipboard.\n")

    user_input = input("Enter MusicBrainz Release MBID URL https://... (or press Enter to read it from the clipboard, or type skip): ").strip()

    if user_input.lower() == "skip":
        return None

    if user_input:
        mbid = extract_mbid_from_text(user_input)
        if mbid:
            return mbid
        print("No valid MBID found in input.")
        return None

    clip = get_clipboard_text()
    mbid = extract_mbid_from_text(clip)

    if mbid:
        print(f"Using MBID from clipboard: {mbid}")
        return mbid

    print("No valid MBID found in clipboard.")
    return None


def get_release_by_mbid(mbid):
    try:
        result = mb_with_retry(mb.get_release_by_id, mbid, includes=["recordings", "artists"])
        release = result["release"]

        # ---- ARTIST (robust extraction) ----
        artist = ""

        if "artist-credit" in release and release["artist-credit"]:
            ac = release["artist-credit"][0]
            if isinstance(ac, dict) and "artist" in ac:
                artist = ac["artist"].get("name", "")
            elif isinstance(ac, dict) and "name" in ac:
                artist = ac.get("name", "")
        elif "artist-credit-phrase" in release:
            artist = release.get("artist-credit-phrase", "")

        # ---- ALBUM ----
        album = release.get("title", "")

        # ---- YEAR ----
        date = release.get("date", "")
        year = date[:4] if date else ""

        mbid = release.get("id", mbid)

        return artist, album, year, mbid

    except Exception as e:
        print(f"Failed to fetch release for MBID {mbid}: {e}")
        return None, None, None, None


def print_track_durations(drive):
    try:
        disc = discid.read(drive)
        print("\nTrack list (for identification):")
        print("---------------------------------")

        for i, t in enumerate(disc.tracks, start=1):
            seconds = t.length // 75
            mm = seconds // 60
            ss = seconds % 60
            print(f"{i:2d}. {mm:02d}:{ss:02d}")

        print("---------------------------------")
        print("Use this + artist/album to search on https://musicbrainz.org\n")

    except Exception as e:
        print(f"Failed to read track durations: {e}")


# ---------- MAIN LOOP ----------

if __name__ == "__main__":
    print("Waiting for CD insertion on all drives...")

    last_disc_ids = {drive: None for drive in DRIVES}

    while True:
        try:
            for drive in DRIVES:
                current_disc_id = get_current_disc_id(drive)
                last_disc_id = last_disc_ids[drive]

                if current_disc_id and current_disc_id != last_disc_id:
                    print(f"\n[{drive}] CD detected. Processing...")
                    time.sleep(2)

                    artist, album, year, mbid = get_musicbrainz_metadata(drive)
                    genre = ""

                    if not artist:
                        print(f"[{drive}] Not found by disc ID.")

                        # 1. Print track durations
                        print_track_durations(drive)

                        # 2. Eject tray so user can grab disc + work
                        eject_cd(drive)
                        print(f"[{drive}] CD tray ejected.")

                        # 3. Prompt for MBID (clipboard first)
                        mbid_input = prompt_for_mbid_with_clipboard()
                        if mbid_input:
                            artist, album, year, mbid = get_release_by_mbid(mbid_input)

                        # 4. Artist/Album fallback
                        if not artist:
                            user_artist, user_album = prompt_for_artist_album()

                            if user_artist and user_album:
                                artist, album, year, mbid = search_mb_by_artist_album(user_artist, user_album)

                                if not artist:
                                    artist, album, year, genre = search_discogs_by_artist_album(user_artist, user_album)

                        if not artist:
                            print(f"[{drive}] No match found. Skipping.")
                            last_disc_ids[drive] = current_disc_id
                            continue



                    if not genre:
                        genre = get_discogs_genre(artist, album)

                    year_clean = clean_year(year)

                    row = {
                        "drive": drive,
                        "artist": artist,
                        "album": album,
                        "year": year_clean,
                        "genre": genre,
                        "mbid": mbid
                    }

                    print(f"[{drive}] Identified:")
                    print(row)

                    append_to_csv(row)
                    print(f"[{drive}] Saved to {CSV_PATH}")

                    eject_cd(drive)
                    print(f"[{drive}] CD tray ejected.")

                    last_disc_ids[drive] = current_disc_id

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)
