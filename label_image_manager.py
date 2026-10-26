import tempfile

import musicbrainzngs as mb
import qrcode
from PIL import Image, ImageDraw, ImageFont

from label_config import (
    LABEL_WIDTH,
    LABEL_HEIGHT,
    SAFE_LEFT,
    SAFE_RIGHT,
    SAFE_TOP,
    SAFE_BOTTOM,
    QR_SIZE,
    LINE_SPACING,
    TITLE_FONT_SIZE,
    TRACK_FONT_SIZE,
)

HEADER_Y = SAFE_TOP + 0
SUBHEADER_Y = SAFE_TOP + 60
TRACKS_Y = SAFE_TOP + 130

FONT_TITLE = ImageFont.truetype("arialbd.ttf", TITLE_FONT_SIZE)
FONT_TRACK = ImageFont.truetype("arial.ttf", TRACK_FONT_SIZE)


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


def generate_label_image(artist, album, year, genre, mbid):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    out_path = tmp.name
    tmp.close()

    img = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # HEADER
    draw.text((SAFE_LEFT, HEADER_Y), artist, fill="black", font=FONT_TITLE)
    draw.text((SAFE_LEFT, SUBHEADER_Y), album, fill="black", font=FONT_TRACK)

    # YEAR / GENRE (RIGHT)
    right_x = LABEL_WIDTH - SAFE_RIGHT

    year_w = 0
    genre_w = 0

    if year:
        bbox = draw.textbbox((0, 0), year, font=FONT_TITLE)
        year_w = bbox[2] - bbox[0]

    if genre:
        bbox = draw.textbbox((0, 0), genre, font=FONT_TRACK)
        genre_w = bbox[2] - bbox[0]

    col_w = max(year_w, genre_w)

    if year:
        draw.text((right_x - col_w, HEADER_Y), year, fill="black", font=FONT_TITLE)

    if genre:
        draw.text((right_x - col_w, SUBHEADER_Y), genre, fill="black", font=FONT_TRACK)

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
    max_y = LABEL_HEIGHT - SAFE_BOTTOM
    qr_cutoff_y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM - 20
    truncated = False

    for idx, title in enumerate(tracks, start=1):

        if y >= qr_cutoff_y:
            max_text_width = LABEL_WIDTH - QR_SIZE - SAFE_RIGHT - SAFE_LEFT - 20
        else:
            max_text_width = LABEL_WIDTH - SAFE_RIGHT - SAFE_LEFT

        line = f"{idx}. {title}"
        wrapped = wrap_text(draw, line, FONT_TRACK, max_text_width)

        for wline in wrapped:
            if y + LINE_SPACING > max_y:
                truncated = True
                break

            draw.text((SAFE_LEFT, y), wline, fill="black", font=FONT_TRACK)
            y += LINE_SPACING

        if truncated:
            break

    if truncated:
        draw.text((SAFE_LEFT, y), "...", fill="black", font=FONT_TRACK)

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
