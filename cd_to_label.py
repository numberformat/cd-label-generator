import tempfile, discid, discogs_client, time, ctypes, os, string, win32file, win32con, win32print, win32ui, qrcode
import musicbrainzngs as mb
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageWin
from dotenv import load_dotenv

# ===================== CONFIG =====================

OUT_DIR = "data/auto_labels"
PRINTER_NAME = "DYMO LabelWriter 4XL"

# 4x6 landscape (confirmed working)
LABEL_WIDTH  = 1800
LABEL_HEIGHT = 1200

SAFE_LEFT   = 40
SAFE_RIGHT  = 500
SAFE_TOP    = 40
SAFE_BOTTOM = 80

HEADER_Y    = SAFE_TOP + 0
SUBHEADER_Y = SAFE_TOP + 60
TRACKS_Y    = SAFE_TOP + 130

QR_SIZE = 250

LINE_SPACING     = 46
TRACK_FONT_SIZE  = 36
ARTIST_FONT_SIZE = 50
ALBUM_FONT_SIZE  = 40

# ================================================

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

mb.set_useragent("CDLabeler", "1.0", "you@example.com")

FONT_BOLD  = ImageFont.truetype("arialbd.ttf", ARTIST_FONT_SIZE)
FONT_REG   = ImageFont.truetype("arial.ttf", ALBUM_FONT_SIZE)
FONT_TRACK = ImageFont.truetype("arial.ttf", TRACK_FONT_SIZE)


# ===================== DISCOGS TOKEN =====================

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

    return token


DISCOGS_TOKEN = get_discogs_token()


# ===================== DRIVE DETECTION =====================

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


# ===================== CORE HELPERS =====================

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
            includes=["artists", "recordings"]
        )

        release = result["disc"]["release-list"][0]

        artist = release["artist-credit"][0]["artist"]["name"]
        album = release["title"]
        year = release.get("date", "")[:4]
        mbid = release["id"]

        return artist, album, year, mbid

    except:
        return None, None, None, None


def get_discogs_genre(artist, album):
    try:
        d = discogs_client.Client(
            "CDLabeler/1.0",
            user_token=DISCOGS_TOKEN
        )
        results = d.search(artist=artist, release_title=album, type="release")
        if results:
            r = results[0]
            if r.genres:
                return r.genres[0]
    except:
        pass

    return ""


def clean_year(y):
    try:
        return str(int(float(y)))
    except:
        return ""


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = current + (" " if current else "") + w
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines


# ===================== SEARCH HELPERS =====================

def search_mb_by_artist_album(artist, album):
    query = f'artist:"{artist}" AND release:"{album}"'
    try:
        result = mb.search_releases(query=query, limit=10)
        releases = result.get("release-list", [])
    except Exception:
        releases = []

    if not releases:
        return None, None, None, None

    r = releases[0]
    mbid = r.get("id")
    return (
        r.get("artist-credit", [{}])[0].get("artist", {}).get("name", ""),
        r.get("title", ""),
        r.get("date", "")[:4],
        mbid,
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
    print("Metadata not found. Please enter artist/album to search.")
    artist = input("Artist: ").strip()
    album = input("Album: ").strip()
    if not artist or not album:
        return None, None
    return artist, album


# ===================== LABEL GENERATOR =====================

def generate_label_image(artist, album, year, genre, mbid):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    out_path = tmp.name
    tmp.close()

    img = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # HEADER
    draw.text((SAFE_LEFT, HEADER_Y), artist, fill="black", font=FONT_BOLD)
    draw.text((SAFE_LEFT, SUBHEADER_Y), album, fill="black", font=FONT_REG)

    # YEAR / GENRE (RIGHT)
    right_x = LABEL_WIDTH - SAFE_RIGHT

    year_w = 0
    genre_w = 0

    if year:
        bbox = draw.textbbox((0, 0), year, font=FONT_BOLD)
        year_w = bbox[2] - bbox[0]

    if genre:
        bbox = draw.textbbox((0, 0), genre, font=FONT_REG)
        genre_w = bbox[2] - bbox[0]

    col_w = max(year_w, genre_w)

    if year:
        draw.text((right_x - col_w, HEADER_Y), year, fill="black", font=FONT_BOLD)

    if genre:
        draw.text((right_x - col_w, SUBHEADER_Y), genre, fill="black", font=FONT_REG)

    # TRACK LIST (from MusicBrainz)
    tracks = []
    try:
        result = mb.get_release_by_id(mbid, includes=["recordings"])
        media = result["release"].get("medium-list", [])
        for medium in media:
            track_list = medium.get("track-list", [])
            for t in track_list:
                tracks.append(t["recording"]["title"])
    except:
        pass

    y = TRACKS_Y
    MAX_Y = LABEL_HEIGHT - SAFE_BOTTOM
    QR_CUTOFF_Y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM - 20
    truncated = False

    for idx, title in enumerate(tracks, start=1):

        if y >= QR_CUTOFF_Y:
            max_text_width = LABEL_WIDTH - QR_SIZE - SAFE_RIGHT - SAFE_LEFT - 20
        else:
            max_text_width = LABEL_WIDTH - SAFE_RIGHT - SAFE_LEFT

        line = f"{idx}. {title}"
        wrapped = wrap_text(draw, line, FONT_TRACK, max_text_width)

        for wline in wrapped:
            if y + LINE_SPACING > MAX_Y:
                truncated = True
                break

            draw.text((SAFE_LEFT, y), wline, fill="black", font=FONT_TRACK)
            y += LINE_SPACING

        if truncated:
            break

    if truncated:
        draw.text((SAFE_LEFT, y), "…", fill="black", font=FONT_TRACK)

    # ---------------------------
    # QR CODE (BOTTOM RIGHT)
    # ---------------------------
    qr_x = LABEL_WIDTH - QR_SIZE - SAFE_RIGHT
    qr_y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM

    if mbid:
        qr_payload = f"https://musicbrainz.org/release/{mbid}"
        qr = qrcode.make(qr_payload).resize((QR_SIZE, QR_SIZE))
        img.paste(qr, (qr_x, qr_y))

    img.save(out_path, format="PNG")
    return out_path


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
                        print(f"[{drive}] Not found in MusicBrainz. Ejecting and asking for artist/album...")
                        eject_cd(drive)
                        user_artist, user_album = prompt_for_artist_album()
                        if user_artist and user_album:
                            artist, album, year, mbid = search_mb_by_artist_album(user_artist, user_album)
                            if not artist:
                                artist, album, year, genre = search_discogs_by_artist_album(user_artist, user_album)

                        if not artist:
                            print(f"[{drive}] Not found in any source. Ejecting.")
                            last_disc_ids[drive] = current_disc_id
                            continue

                    if not genre:
                        genre = get_discogs_genre(artist, album)
                    year_clean = clean_year(year)

                    print(f"[{drive}] {artist} - {album} ({year_clean}) [{genre}]")

                    label_path = generate_label_image(
                        artist, album, year_clean, genre, mbid
                    )

                    print(f"[{drive}] Label generated: {label_path}")

                    time.sleep(1)
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
