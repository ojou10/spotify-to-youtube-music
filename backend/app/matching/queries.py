from app.domain.models import SourceItemValue
from app.matching.normalize import normalize_text


def build_queries(source: SourceItemValue) -> list[str]:
    artists = [artist.strip() for artist in source.artists if artist.strip()]
    if not artists:
        return [source.title.strip()]
    primary = artists[0]
    title = source.title.strip()
    album = source.album.strip() if source.album else ""
    simplified = normalize_text(title)
    queries = [
        f"{title} {', '.join(artists)}",
        f"{title} {primary}",
        f"{title} {primary} {album}" if album else f"{title} {primary}",
        f"{simplified} {primary}",
    ]
    result: list[str] = []
    for query in queries:
        if query and query not in result:
            result.append(query)
    return result
