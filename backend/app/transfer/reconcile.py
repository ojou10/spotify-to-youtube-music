from collections.abc import Sequence


class DestinationConflict(ValueError):
    pass


def reconcile_prefix(base_length: int, observed: Sequence[str], planned: Sequence[str]) -> int:
    del base_length
    if len(observed) > len(planned) or list(observed) != list(planned[: len(observed)]):
        raise DestinationConflict("destination tail no longer matches the planned ordered append")
    return len(observed)
