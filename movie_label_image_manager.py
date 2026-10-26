# movie_label_image_manager.py
import tempfile
from PIL import Image, ImageDraw, ImageFont
import qrcode

from label_config import (
    LABEL_WIDTH,
    LABEL_HEIGHT,
    SAFE_LEFT,
    SAFE_RIGHT,
    SAFE_TOP,
    SAFE_BOTTOM,
    QR_SIZE,
    LINE_SPACING,
    MOVIE_TITLE_FONT_SIZE,
    MOVIE_META_FONT_SIZE,
    MOVIE_BODY_FONT_SIZE,
)

HEADER_Y = SAFE_TOP + 0
META_Y   = SAFE_TOP + 70
BODY_Y   = SAFE_TOP + 150

FONT_TITLE = ImageFont.truetype("arialbd.ttf", MOVIE_TITLE_FONT_SIZE)
FONT_META  = ImageFont.truetype("arial.ttf", MOVIE_META_FONT_SIZE)
FONT_BODY  = ImageFont.truetype("arial.ttf", MOVIE_BODY_FONT_SIZE)

def wrap_text(draw, text, font, max_width):
    words = (text or "").split()
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

def truncate_lines(lines, max_lines):
    if len(lines) <= max_lines:
        return lines, False
    return lines[:max_lines], True

def generate_movie_label_image(
    title: str,
    release_date: str,
    runtime_min: int | None,
    rating: str | None,
    user_rating: float | None,
    budget: int | None,
    genres: list[dict] | None,
    synopsis: str,
    cast: list[str] | None,
    tmdb_id: int,
):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    out_path = tmp.name
    tmp.close()

    img = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((SAFE_LEFT, HEADER_Y), title or "", fill="black", font=FONT_TITLE)

    # Rating under title (left)
    rating_text = (rating or "").strip()
    user_rating_str = ""
    if isinstance(user_rating, (float, int)):
        user_rating_str = f"{round(user_rating * 10):d}%"
    budget_str = ""
    if isinstance(budget, (int, float)) and budget > 0:
        budget_str = f"${int(budget):,}"
    genre_names = []
    for entry in genres or []:
        name = (entry.get("name") or "").strip()
        if name:
            genre_names.append(name)
    genre_text = ", ".join(genre_names)
    if len(genre_text) > 50:
        genre_text = genre_text[:50].rstrip(", ")

    if rating_text or genre_text:
        parts = []
        if rating_text:
            parts.append(f"Rating: {rating_text}")
        if genre_text:
            parts.append(f"{genre_text}")
        draw.text(
            (SAFE_LEFT, META_Y),
            "    ".join(parts),
            fill="black",
            font=FONT_META,
        )

    # Year and runtime (right column)
    year = (release_date or "")[:4] if release_date else ""
    runtime_str = f"{runtime_min} min" if runtime_min else ""
    right_x = LABEL_WIDTH - SAFE_RIGHT

    year_w = 0
    runtime_w = 0

    if year:
        bbox = draw.textbbox((0, 0), year, font=FONT_TITLE)
        year_w = bbox[2] - bbox[0]

    if runtime_str:
        bbox = draw.textbbox((0, 0), runtime_str, font=FONT_META)
        runtime_w = bbox[2] - bbox[0]

    col_w = max(year_w, runtime_w)

    if year:
        draw.text((right_x - col_w, HEADER_Y), year, fill="black", font=FONT_TITLE)

    if runtime_str:
        draw.text((right_x - col_w, META_Y), runtime_str, fill="black", font=FONT_META)

    # Body (synopsis)
    max_y = LABEL_HEIGHT - SAFE_BOTTOM
    tmdb_score_y = META_Y + 70
    synopsis_start_y = tmdb_score_y + 85
    y = synopsis_start_y

    # reduce width when overlapping QR zone
    full_width = LABEL_WIDTH - SAFE_LEFT - SAFE_RIGHT
    narrow_width = LABEL_WIDTH - SAFE_LEFT - SAFE_RIGHT - QR_SIZE - 20
    summary_meta_parts = []
    if user_rating_str:
        summary_meta_parts.append(f"TMDB Score: {user_rating_str}")
    if budget_str:
        summary_meta_parts.append(f"Budget: {budget_str}")
    if summary_meta_parts:
        draw.text(
            (SAFE_LEFT, tmdb_score_y),
            "    ".join(summary_meta_parts),
            fill="black",
            font=FONT_META,
        )

    synopsis = synopsis or ""
    cast = cast or []
    cast_line = ""
    if cast:
        cast_line = "Cast: " + ", ".join(cast)

    # Pre-wrap using the narrower width so we don’t reflow mid-way (simpler and stable)
    lines = wrap_text(draw, synopsis, FONT_BODY, narrow_width)
    if cast_line:
        cast_lines = wrap_text(draw, cast_line, FONT_BODY, narrow_width)
        if lines:
            lines.append("")
        lines.extend(cast_lines)

    # Compute max lines available
    available_height = (max_y - synopsis_start_y)
    max_lines = max(1, available_height // LINE_SPACING)

    lines, truncated = truncate_lines(lines, max_lines)

    for line in lines:
        if y + LINE_SPACING > max_y:
            truncated = True
            break
        draw.text((SAFE_LEFT, y), line, fill="black", font=FONT_BODY)
        y += LINE_SPACING

    if truncated and y + LINE_SPACING <= max_y:
        draw.text((SAFE_LEFT, y), "…", fill="black", font=FONT_BODY)

    # QR (TMDb URL)
    qr_x = LABEL_WIDTH - QR_SIZE - SAFE_RIGHT
    qr_y = LABEL_HEIGHT - QR_SIZE - SAFE_BOTTOM
    qr_payload = f"https://www.themoviedb.org/movie/{tmdb_id}"
    qr = qrcode.make(qr_payload).resize((QR_SIZE, QR_SIZE))
    img.paste(qr, (qr_x, qr_y))

    img.save(out_path, format="PNG")
    return out_path
