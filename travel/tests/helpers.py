"""Shared helpers for mocking the Art Institute of Chicago client in tests.

We never hit the real API in tests: fetch_artwork is patched wherever it is
imported (serializers/project.py and serializers/place.py each import their
own reference, so both patch targets are needed).
"""


def fake_artwork(external_id: str) -> dict:
    """Build a fake successful response, shaped like artic_client.fetch_artwork()."""
    return {
        "external_id": str(external_id),
        "title": f"Artwork {external_id}",
        "image_id": f"img-{external_id}",
    }


def fetch_artwork_side_effect(known_ids=None, missing_ids=None):
    """
    Returns a function suitable as a Mock(side_effect=...) for fetch_artwork.

    - IDs in `missing_ids` resolve to None (not found in the third-party API).
    - Everything else resolves to a fake artwork (default: "unknown" treated as valid,
      unless explicitly listed in missing_ids).
    """
    missing_ids = set(missing_ids or [])

    def _side_effect(external_id):
        if external_id in missing_ids:
            return None
        return fake_artwork(external_id)

    return _side_effect
