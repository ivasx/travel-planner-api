import requests
from django.core.cache import cache

ARTIC_BASE_URL = "https://api.artic.edu/api/v1/artworks"
CACHE_TTL_SECONDS = 3600  # 1 hour


def fetch_artwork(external_id: str) -> dict | None:
    cache_key = f"artic_artwork:{external_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(f"{ARTIC_BASE_URL}/{external_id}", timeout=5)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    payload = response.json().get("data")
    if not payload:
        return None

    artwork = {
        "external_id": str(payload.get("id")),
        "title": payload.get("title", ""),
        "image_id": payload.get("image_id"),
    }

    cache.set(cache_key, artwork, timeout=CACHE_TTL_SECONDS)
    return artwork
