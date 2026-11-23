from __future__ import annotations

from dbc_askdata.observability.turn import (
    TURN_STATUS_OK,
    bind_turn,
    clear_turn,
    get_bound_turn_id,
)


def test_bind_and_clear_turn_context():
    clear_turn()
    assert get_bound_turn_id() is None
    bind_turn(42)
    assert get_bound_turn_id() == 42
    clear_turn()
    assert get_bound_turn_id() is None
    assert TURN_STATUS_OK == "OK"
