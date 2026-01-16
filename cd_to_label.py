import time, os, win32ui
from pathlib import Path
from PIL import Image, ImageWin
from label_image_manager import generate_label_image
from drive_manager import (
    get_optical_drives,
    get_current_disc_id,
    print_track_durations,
    eject_cd,
)
from musicbrainz_manager import (
    init_musicbrainz,
    get_release_by_mbid,
    get_musicbrainz_metadata,
    search_mb_by_artist_album,
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

# ===================== CONFIG =====================
DEBUG = True
OUT_DIR = "data/auto_labels"
PRINTER_NAME = "DYMO LabelWriter 4XL"

# ================================================

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

init_musicbrainz()

# ===================== DISCOGS TOKEN =====================
DISCOGS_TOKEN = get_discogs_token()
# ===================== DRIVE DETECTION =====================
DRIVES = get_optical_drives()

if not DRIVES:
    print("No optical drives found. Exiting.")
    exit(1)

print(f"Detected optical drives: {', '.join(DRIVES)}")

# ===================== PRINTING =====================

def print_image_to_dymo(image_path, printer_name=PRINTER_NAME):
    img = Image.open(image_path)

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)

    hdc.StartDoc("CD Label")
    hdc.StartPage()

    dib = ImageWin.Dib(img)

    width = hdc.GetDeviceCaps(8)
    height = hdc.GetDeviceCaps(10)

    dib.draw(hdc.GetHandleOutput(), (0, 0, width, height))

    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


# ===================== MAIN LOOP =====================

if __name__ == "__main__":
    print("Waiting for CD insertion on any drive...")

    last_disc_ids = {drive: None for drive in DRIVES}

    while True:
        try:
            for drive in DRIVES:
                current_disc_id = get_current_disc_id(drive)
                last_disc_id = last_disc_ids[drive]

                if current_disc_id and current_disc_id != last_disc_id:
                    print(f"[{drive}] CD detected. Reading metadata...")

                    time.sleep(2)  # drive settle

                    artist, album, year, mbid = get_musicbrainz_metadata(drive)
                    genre = ""

                    if not artist:
                        print(f"[{drive}] Not found in MusicBrainz.")
                        print_track_durations(drive)
                        eject_cd(drive)

                        mbid_input = prompt_for_mbid_with_clipboard()
                        if mbid_input:
                            artist, album, year, mbid = get_release_by_mbid(mbid_input)

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
                            print(f"[{drive}] Not found in any source. Ejecting.")
                            last_disc_ids[drive] = current_disc_id
                            continue

                    if not genre:
                        genre = get_discogs_genre(artist, album, token=DISCOGS_TOKEN)
                    year_clean = clean_year(year)

                    print(f"[{drive}] {artist} - {album} ({year_clean}) [{genre}]")

                    label_path = generate_label_image(
                        artist, album, year_clean, genre, mbid
                    )

                    print(f"[{drive}] Label generated: {label_path}")

                    time.sleep(1)
                    if not DEBUG:
                        print_image_to_dymo(label_path)
                        try:
                            os.remove(label_path)
                        except:
                            pass                    
                    print(f"[{drive}] Label printed.")

                    time.sleep(1)
                    eject_cd(drive)
                    print(f"[{drive}] CD tray ejected.")

                    last_disc_ids[drive] = current_disc_id

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)
