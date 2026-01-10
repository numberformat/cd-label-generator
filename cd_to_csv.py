import discid
import musicbrainzngs as mb
import discogs_client
import pandas as pd
from pathlib import Path
import time
import ctypes
import os
from dotenv import load_dotenv
import win32api
import string
import win32file
import win32con

# ---------------- CONFIG ----------------
CSV_PATH = "data/cd_labels.csv"
# ----------------------------------------

mb.set_useragent("CDLabeler", "1.0", "you@example.com")


# ---------- ENV / TOKEN HANDLING ----------

def get_discogs_token():
    load_dotenv()

    token = os.getenv("DISCOGS_TOKEN")
    if token:
        return token

    print("\nDiscogs token not found.")
    print("You can create one at: https://www.discogs.com/settings/developers\n")
    token = input("Enter your Discogs user token: ").strip()

    # save to .env for next time
    with open(".env", "a", encoding="utf-8") as f:
        f.write(f"\nDISCOGS_TOKEN={token}\n")

    print("Saved token to .env\n")
    return token


DISCOGS_TOKEN = get_discogs_token()


# ---------- DRIVE DETECTION ----------

def get_optical_drives():
    drives = []

    # Method 1: Win32 API (fast)
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

    # Method 2: Fallback – probe discid directly
    if not drives:
        for letter in string.ascii_uppercase:
            drive = f"{letter}:"
            try:
                discid.read(drive)
                drives.append(drive)
            except:
                pass

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

        result = mb.get_releases_by_discid(
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
    d = discogs_client.Client(
        "CDLabeler/1.0",
        user_token=DISCOGS_TOKEN
    )

    results = d.search(artist=artist, release_title=album, type="release")

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
                    print(f"[{drive}] CD detected. Processing...")

                    time.sleep(2)  # drive settle time

                    artist, album, year, mbid = get_musicbrainz_metadata(drive)

                    # retry once to avoid race condition
                    if artist is None:
                        print(f"[{drive}] Not found, retrying once...")
                        time.sleep(2)
                        artist, album, year, mbid = get_musicbrainz_metadata(drive)

                    if artist is None:
                        print(f"[{drive}] CD not found in MusicBrainz. Skipping and ejecting.")
                        eject_cd(drive)
                        print(f"[{drive}] CD tray ejected.")
                        last_disc_ids[drive] = current_disc_id
                        continue

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

                    print(f"[{drive}] Detected:")
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
