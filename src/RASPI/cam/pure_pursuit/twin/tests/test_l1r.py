from pure_pursuit.l1r import possible_colors
from pure_pursuit.wro_field import PARKING_FORBIDDEN_SEATS, SEATS, SECTIONS_CW, randomize


def test_hypotheses_retain_official_draws_under_partial_observations():
    for seed in range(1, 25):
        field = randomize(seed)
        truth = {(s.section, s.seat): s.color for s in field.signs}
        known = dict(list(truth.items())[::2])
        empty = {(sec, seat) for sec in SECTIONS_CW[::2] for seat in SEATS} - truth.keys()
        remaining = possible_colors(field.direction, field.parking_section, known, empty)
        assert remaining is not None
        assert all(color in remaining[k] for k, color in truth.items())
        assert all(not remaining[field.parking_section, seat] for seat in PARKING_FORBIDDEN_SEATS)


def test_impossible_observations_fall_back_without_pruning():
    assert possible_colors("CW", "N", {("N", "X2"): "Green"}, set()) is None


def test_complete_field_removes_empty_seats_and_preserves_color():
    field = randomize(9)
    truth = {(s.section, s.seat): s.color for s in field.signs}
    empty = {(sec, seat) for sec in SECTIONS_CW for seat in SEATS} - truth.keys()
    remaining = possible_colors(field.direction, field.parking_section, truth, empty)
    assert all(remaining[k] == {color} for k, color in truth.items())
    assert all(not remaining[k] for k in empty)


def test_pass_side_is_saved_only_after_a_legal_pass():
    from pure_pursuit.route_mode import RouteMode

    mode = RouteMode.__new__(RouteMode)
    mode._l1_pass_sides = {}
    seat = ("N", "T1")
    mode._record_l1_passes("CW", (450, 650, 90), {seat: "Red"})
    mode._record_l1_passes("CW", (660, 1150, 90), {seat: "Red"})
    assert not mode._l1_pass_sides
    mode._record_l1_passes("CW", (660, 650, 90), {seat: "Red"})
    assert mode._l1_pass_sides == {seat: "Red"}


def test_braking_corridor_uses_the_swept_body_and_ignores_impossible_seats():
    from types import SimpleNamespace

    import numpy as np

    from pure_pursuit.route_mode import RouteMode

    mode = RouteMode.__new__(RouteMode)
    mode.follower = SimpleNamespace(i=0, cte=0)
    mode.route = SimpleNamespace(length_mm=1000, x=np.arange(0, 1000, 10),
                                 y=np.full(100, 900), heading_deg=np.full(100, 90))
    seat = ("N", "T1")
    assert mode._l1_path_risks([seat], set()) == [seat]
    assert not mode._l1_path_risks([seat], {seat})
    mode.route.y = np.full(100, 1250)
    assert not mode._l1_path_risks([seat], set())
