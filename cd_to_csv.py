import time

from file_manager import append_to_csv
from drive_manager import (
    get_optical_drives,
    get_current_disc_id,
    print_track_durations,
    eject_cd,
)
from musicbrainz_manager import (
    init_musicbrainz,
    search_mb_by_artist_album,
    get_musicbrainz_metadata,
    get_release_by_mbid,
)
from discogs_manager import (
    get_discogs_token,
    get_discogs_genre,
    search_discogs_by_artist_album,
)
from common_helper import (
    prompt_for_mbid_with_clipboard,
    prompt_for_artist_album,
    clean_year,
)

# ---------------- CONFIG ----------------
CSV_PATH = "data/cd_labels.csv"
# ---------------------------------------

init_musicbrainz()

# ---------- ENV / TOKEN HANDLING ----------

DISCOGS_TOKEN = get_discogs_token()

# ---------- DRIVE DETECTION ----------

DRIVES = get_optical_drives()

if not DRIVES:
    print("No optical drives found. Exiting.")
    exit(1)

print(f"Detected optical drives: {', '.join(DRIVES)}")

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
                                    artist, album, year, genre = search_discogs_by_artist_album(
                                        user_artist,
                                        user_album,
                                        token=DISCOGS_TOKEN
                                    )

                        if not artist:
                            print(f"[{drive}] No match found. Skipping.")
                            last_disc_ids[drive] = current_disc_id
                            continue



                    if not genre:
                        genre = get_discogs_genre(artist, album, token=DISCOGS_TOKEN)

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

                    append_to_csv(row, CSV_PATH)
                    print(f"[{drive}] Saved to {CSV_PATH}")

                    eject_cd(drive)
                    print(f"[{drive}] CD tray ejected.")

                    last_disc_ids[drive] = current_disc_id

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)
