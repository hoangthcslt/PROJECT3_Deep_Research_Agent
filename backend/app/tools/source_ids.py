"""Stable citation IDs for URL-backed sources."""

import hashlib


def source_id_for_url(url: str) -> str:
    return "REF_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
