# movie_to_label.py
import os
import time
import win32ui
from PIL import Image, ImageWin

from tmdb_manager import (
    TMDbError,
    get_tmdb_api_key,
    search_movies,
    get_movie_details,
    get_movie_cast,
    get_movie_certification,
    prompt_select_movie,
)
from movie_label_image_manager import generate_movie_label_image

DEBUG = False
PRINTER_NAME = "DYMO LabelWriter 4XL"

def print_image_to_dymo(image_path, printer_name=PRINTER_NAME):
    img = Image.open(image_path)

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)

    hdc.StartDoc("Movie Label")
    hdc.StartPage()

    dib = ImageWin.Dib(img)
    width = hdc.GetDeviceCaps(8)
    height = hdc.GetDeviceCaps(10)
    dib.draw(hdc.GetHandleOutput(), (0, 0, width, height))

    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()

def main():
    api_key = get_tmdb_api_key()

    while True:
        try:
            title = input("Enter movie title (Press Ctrl-C to quit): ").strip()
            if not title:
                print("No title entered.")
                continue

            results = search_movies(title, api_key=api_key)
            if not results:
                print("No matches found.")
                continue

            if len(results) == 1:
                movie_id = results[0]["id"]
            else:
                movie_id = prompt_select_movie(results)

            details = get_movie_details(movie_id, api_key=api_key)
            certification = get_movie_certification(movie_id, api_key=api_key)
            cast_names = get_movie_cast(movie_id, api_key=api_key)

            label_path = generate_movie_label_image(
                title=details.get("title") or "",
                release_date=details.get("release_date") or "",
                runtime_min=details.get("runtime"),
                rating=certification,
                user_rating=details.get("vote_average"),
                budget=details.get("budget"),
                genres=details.get("genres") or [],
                synopsis=details.get("overview") or "",
                cast=cast_names,
                tmdb_id=details.get("id"),
            )

            print(f"Label generated: {label_path}")
            time.sleep(0.5)

            if not DEBUG:
                print_image_to_dymo(label_path)
                try:
                    os.remove(label_path)
                except:
                    pass
                print("Label printed.")
            else:
                print("DEBUG=True; not printing.")
        except TMDbError as exc:
            print(exc)
            continue
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
