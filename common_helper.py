import win32clipboard
import re


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

def prompt_for_mbid_with_clipboard(input_func=input, print_func=print):
    print_func("\nManual identification required.")
    print_func("Search on MusicBrainz by:")
    print_func("  - Artist name")
    print_func("  - Album title")
    print_func("  - Track count + durations")
    print_func("\nOpen the correct release page and copy the URL.")
    print_func("Press Enter to use the MBID from your clipboard.\n")

    user_input = input_func(
        "Enter MusicBrainz Release MBID URL https://... (or press Enter to read it from the clipboard, or type skip): "
    ).strip()

    if user_input.lower() == "skip":
        return None

    if user_input:
        mbid = extract_mbid_from_text(user_input)
        if mbid:
            return mbid
        print_func("No valid MBID found in input.")
        return None

    clip = get_clipboard_text()
    mbid = extract_mbid_from_text(clip)

    if mbid:
        print_func(f"Using MBID from clipboard: {mbid}")
        return mbid

    print_func("No valid MBID found in clipboard.")
    return None

   
def prompt_for_artist_album():
    print("\nMetadata not found. Please enter artist and album to search.")
    artist = input("Artist: ").strip()
    album = input("Album: ").strip()
    if not artist or not album:
        return None, None
    return artist, album


def clean_year(y):
    try:
        return str(int(float(y)))
    except:
        return ""
    
