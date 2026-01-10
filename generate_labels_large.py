from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from pathlib import Path
import qrcode
import musicbrainzngs as mb
import time, random

# ---------------- CONFIG ----------------
CSV_PATH = "data/cd_labels.csv"
OUT_DIR = "data/gif_labels_large"

# 4x6 @ 300 DPI (DO NOT CHANGE)
LABEL_WIDTH  = 1800
LABEL_HEIGHT = 1200

# Hard safe margins for DYMO dead zones
SAFE_LEFT   = 40
SAFE_RIGHT  = 500
SAFE_TOP    = 40
SAFE_BOTTOM = 80

HEADER_Y   = SAFE_TOP + 0
SUBHEADER_Y = SAFE_TOP + 60
TRACKS_Y   = SAFE_TOP + 130

QR_SIZE = 250

LINE_SPACING     = 46
TRACK_FONT_SIZE  = 36
ARTIST_FONT_SIZE = 50
ALBUM_FONT_SIZE  = 40
# ---------------------------------------

Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH)

mb.set_useragent("CDLabeler", "1.0", "you@example.com")

FONT_BOLD  = ImageFont.truetype("arialbd.ttf", ARTIST_FONT_SIZE)
FONT_REG   = ImageFont.truetype("arial.ttf", ALBUM_FONT_SIZE)
FONT_TRACK = ImageFont.truetype("arial.ttf", TRACK_FONT_SIZE)


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


def get_track_list(mbid):
    try:
        result = mb_with_retry(mb.get_release_by_id, mbid, includes=["recordings"])
        tracks = []

        media = result["release"].get("medium-list", [])
        for medium in media:
            track_list = medium.get("track-list", [])
            for t in track_list:
                title = t["recording"]["title"]
                tracks.append(title)

        return tracks

    except Exception as e:
        print(f"Failed to fetch tracks for MBID {mbid}: {e}")
        return []


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


for i, r in df.iterrows():
    img = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    artist = str(r["artist"])
    album  = str(r["album"])
    year   = "" if pd.isna(r["year"]) else str(r["year"])
    genre  = "" if pd.isna(r["genre"]) else str(r["genre"])
    mbid   = str(r["mbid"])

    # ---------------------------
    # HEADER (LEFT)
    # ---------------------------
    draw.text((SAFE_LEFT, HEADER_Y), artist, fill="black", font=FONT_BOLD)
    draw.text((SAFE_LEFT, SUBHEADER_Y), album, fill="black", font=FONT_REG)

    # ---------------------------
    # YEAR / GENRE (TOP RIGHT)
    # ---------------------------
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

    # ---------------------------
    # TRACK LIST
    # ---------------------------
    tracks = get_track_list(mbid)

    y = TRACKS_Y

    MAX_Y = LABEL_HEIGHT - SAFE_BOTTOM
    QR_CUTOFF_Y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM - 20
    truncated = False

    for idx, title in enumerate(tracks, start=1):

        # Adjust width if overlapping QR zone
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

    # ---- TRUNCATION INDICATOR ----
    if truncated:
        draw.text((SAFE_LEFT, y), "…", fill="black", font=FONT_TRACK)

    # ---------------------------
    # QR CODE (BOTTOM RIGHT)
    # ---------------------------
    qr_payload = f"https://musicbrainz.org/release/{mbid}"
    qr = qrcode.make(qr_payload).resize((QR_SIZE, QR_SIZE))

    qr_x = LABEL_WIDTH - QR_SIZE - SAFE_RIGHT
    qr_y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM

    img.paste(qr, (qr_x, qr_y))

    out_path = Path(OUT_DIR) / f"label_large_{i}.png"
    img.save(out_path, format="PNG")

    print("Generated:", out_path)

print("All 4x6 labels generated.")
