# test_tmdb.py
from tmdb_manager import get_tmdb_api_key, search_movies, get_movie_details

def main():
    api_key = get_tmdb_api_key()
    results = search_movies("The Matrix", api_key)
    print("Search results:", len(results))

    if results:
        movie_id = results[0]["id"]
        details = get_movie_details(movie_id, api_key)
        print(details["title"])
        print(details["overview"][:120])
        print(details["runtime"])
        print(details["vote_average"])

if __name__ == "__main__":
    main()