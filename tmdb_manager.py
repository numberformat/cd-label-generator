# tmdb_manager.py
import os
import time
import random
import requests
from dotenv import load_dotenv

TMDB_BASE = "https://api.themoviedb.org/3"

class TMDbError(Exception):
    pass

def _retry_get(url: str, params: dict, retries: int = 5, base_delay: float = 1.0):
    attempt = 0
    while True:
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            attempt += 1
            if attempt > retries:
                raise TMDbError(f"TMDb failed after {retries} retries: {e}") from e
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(f"TMDb error: {e} - retrying in {delay:.1f}s (attempt {attempt}/{retries})")
            time.sleep(delay)

def get_tmdb_api_key() -> str:
    load_dotenv()
    key = os.getenv("TMDB_API_KEY", "").strip()
    if key:
        return key

    print("\nTMDB_API_KEY not found in environment/.env.")
    print("Create an API key at https://www.themoviedb.org/settings/api\n")
    while True:
        key = input("Enter your TMDb API key: ").strip()
        if key:
            break
        print("TMDB_API_KEY is required. Please try again.")

    with open(".env", "a", encoding="utf-8") as f:
        f.write(f"\nTMDB_API_KEY={key}\n")

    print("Saved TMDB_API_KEY to .env\n")
    return key

def search_movies(title: str, api_key: str, language: str = "en-US"):
    url = f"{TMDB_BASE}/search/movie"
    params = {
        "api_key": api_key,
        "query": title,
        "include_adult": False,
        "language": language,
    }
    data = _retry_get(url, params)
    return data.get("results", [])

def get_movie_details(movie_id: int, api_key: str, language: str = "en-US"):
    url = f"{TMDB_BASE}/movie/{movie_id}"
    params = {"api_key": api_key, "language": language}
    return _retry_get(url, params)

def get_movie_cast(movie_id: int, api_key: str, max_names: int = 8) -> list[str]:
    url = f"{TMDB_BASE}/movie/{movie_id}/credits"
    params = {"api_key": api_key}
    data = _retry_get(url, params)
    cast = data.get("cast", [])
    names = []
    for entry in cast:
        name = (entry.get("name") or "").strip()
        if name:
            names.append(name)
        if len(names) >= max_names:
            break
    return names

def get_movie_certification(movie_id: int, api_key: str, region: str = "US") -> str:
    url = f"{TMDB_BASE}/movie/{movie_id}/release_dates"
    params = {"api_key": api_key}
    data = _retry_get(url, params)

    results = data.get("results", [])
    primary = None
    for entry in results:
        if entry.get("iso_3166_1") == region:
            primary = entry
            break

    candidates = [primary] if primary else []
    if not primary:
        candidates = results

    for entry in candidates:
        for release in entry.get("release_dates", []):
            cert = (release.get("certification") or "").strip()
            if cert:
                return cert

    return ""

def prompt_select_movie(results, limit: int = 10) -> int:
    shown = results[:limit]
    for i, m in enumerate(shown, start=1):
        title = m.get("title", "")
        date = m.get("release_date") or ""
        year = date[:4] if date else "????"
        print(f"{i:2d}. {title} ({year})")

    while True:
        raw = input("Select movie number (or 'q' to cancel): ").strip().lower()
        if raw == "q":
            raise TMDbError("User cancelled selection.")
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(shown):
                return shown[idx - 1]["id"]
        print("Invalid selection.")
