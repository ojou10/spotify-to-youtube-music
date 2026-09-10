from app.domain.enums import SupportStatus
from app.domain.models import SourceItemValue
from app.matching.queries import build_queries


def test_build_queries_has_stable_order_and_deduplicates():
    source = SourceItemValue(0, "id", "Song", ("Artist",), "Album", 1000, None, SupportStatus.SUPPORTED)
    queries = build_queries(source)
    assert queries == ["Song Artist", "Song Artist Album", "song Artist"]
