import pytest

from app.transfer.reconcile import DestinationConflict, reconcile_prefix


def test_reconcile_accepted_remote_batch_without_duplicate_write():
    assert reconcile_prefix(7, ["a", "b"], ["a", "b", "a", "c"]) == 2


def test_divergent_tail_pauses():
    with pytest.raises(DestinationConflict):
        reconcile_prefix(7, ["a", "unexpected"], ["a", "b", "c"])
