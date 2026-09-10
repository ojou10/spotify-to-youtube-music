from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

MARKER_PATTERNS = {
    "live": r"\blive\b", "acoustic": r"\bacoustic(?: version)?\b", "remix": r"\bremix\b", "cover": r"\bcover\b",
    "karaoke": r"\bkaraoke\b", "sped_up": r"\bsped\s*up\b", "slowed": r"\bslowed(?:\s+and\s+reverb)?\b",
    "instrumental": r"\binstrumental\b", "remastered": r"\b(?:\d{4}\s+)?remaster(?:ed)?\b",
}


@dataclass(frozen=True)
class NormalizedTrack:
    base_title: str
    artists: tuple[str, ...]
    album: str | None
    markers: frozenset[str]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    value = re.sub(r"\bfeat\.?\b|\bft\.?\b|\bfeaturing\b", " and ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _markers(value: str) -> frozenset[str]:
    normalized = normalize_text(value)
    return frozenset(name for name, pattern in MARKER_PATTERNS.items() if re.search(pattern, normalized))


def _base_title(value: str) -> str:
    normalized = normalize_text(value)
    for pattern in MARKER_PATTERNS.values():
        normalized = re.sub(pattern, " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_track(title: str, artists: Sequence[str], album: str | None) -> NormalizedTrack:
    markers = frozenset().union(_markers(title), _markers(album or ""))
    normalized_artists = tuple(sorted({normalize_text(artist) for artist in artists if normalize_text(artist)}))
    return NormalizedTrack(_base_title(title), normalized_artists, normalize_text(album) if album else None, markers)
