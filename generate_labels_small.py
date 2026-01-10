from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from pathlib import Path
import math

CSV_PATH = "data/cd_labels.csv"
OUT_DIR = "data/gif_labels"

LABEL_WIDTH = 560
ROW_HEIGHT = 50
ROW_GAP = 8             # <-- SPACE BETWEEN LABELS
ROWS_PER_LABEL = 8

LABEL_HEIGHT = (ROW_HEIGHT * ROWS_PER_LABEL) + (ROW_GAP * (ROWS_PER_LABEL - 1))

MARGIN = 4
LINE1_OFFSET = 4
LINE2_OFFSET = 30
RIGHT_PADDING = 6

Path(OUT_DIR).mkdir(exist_ok=True)

df = pd.read_csv(CSV_PATH)

FONT_BOLD = ImageFont.truetype("arialbd.ttf", 22)
FONT_REG  = ImageFont.truetype("arial.ttf", 18)


def fit_text(draw, text, font, max_width):
    if not text:
        return text

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    if text_w <= max_width:
        return text

    ellipsis = "…"
    for i in range(len(text), 0, -1):
        candidate = text[:i] + ellipsis
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return candidate

    return ellipsis


total_rows = len(df)
total_labels = math.ceil(total_rows / ROWS_PER_LABEL)

for label_idx in range(total_labels):
    img = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    start = label_idx * ROWS_PER_LABEL
    end = min(start + ROWS_PER_LABEL, total_rows)
    block = df.iloc[start:end]

    for row_idx, (_, r) in enumerate(block.iterrows()):
        y_base = row_idx * (ROW_HEIGHT + ROW_GAP)

        artist = str(r["artist"])
        album  = str(r["album"])
        year = "" if pd.isna(r["year"]) else str(r["year"])
        genre  = str(r["genre"]) if not pd.isna(r["genre"]) else ""

        # Measure right-aligned fields
        bbox_year = draw.textbbox((0, 0), year, font=FONT_BOLD)
        year_w = bbox_year[2] - bbox_year[0]

        genre_w = 0
        if genre:
            bbox_genre = draw.textbbox((0, 0), genre, font=FONT_REG)
            genre_w = bbox_genre[2] - bbox_genre[0]

        text_right_limit = LABEL_WIDTH - MARGIN

        # Compute safe widths
        line1_max_width = (text_right_limit - RIGHT_PADDING - year_w) - MARGIN
        line2_max_width = (text_right_limit - RIGHT_PADDING - genre_w) - MARGIN

        line1_max_width = max(10, line1_max_width)
        line2_max_width = max(10, line2_max_width)

        # Fit text
        artist_fit = fit_text(draw, artist, FONT_BOLD, line1_max_width)
        album_fit  = fit_text(draw, album,  FONT_REG,  line2_max_width)

        # Draw line 1
        draw.text((MARGIN, y_base + LINE1_OFFSET), artist_fit, fill="black", font=FONT_BOLD)
        draw.text((text_right_limit - year_w, y_base + LINE1_OFFSET), year, fill="black", font=FONT_BOLD)

        # Draw line 2
        draw.text((MARGIN, y_base + LINE2_OFFSET), album_fit, fill="black", font=FONT_REG)

        if genre:
            draw.text((text_right_limit - genre_w, y_base + LINE2_OFFSET), genre, fill="black", font=FONT_REG)

    out_path = Path(OUT_DIR) / f"label_block_{label_idx+1}.gif"
    img.save(out_path, format="GIF")

    print(f"Generated: {out_path}")

print("All labels generated with spacing.")
