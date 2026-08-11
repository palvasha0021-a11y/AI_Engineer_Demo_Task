import hashlib
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking params, trailing slashes, and lowercasing scheme/host."""
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Keep path clean, remove trailing slash
    path = parsed.path.rstrip("/")
    # Reassemble without query params like utm_source for deduplication
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",  # params
        "",  # query
        ""   # fragment
    ))
    return normalized


def generate_fingerprint(*args: str) -> str:
    """Generate SHA-256 fingerprint from one or more input strings."""
    combined = "|".join(str(a).strip().lower() for a in args if a)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
