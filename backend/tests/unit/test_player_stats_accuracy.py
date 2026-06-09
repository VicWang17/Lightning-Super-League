from app.routers.players import _bounded_success, _calc_accuracy
from app.services.match_simulator import _accuracy_ratio


def test_calc_accuracy_is_bounded_for_legacy_inflated_success_counts():
    assert _bounded_success(20, 1800) == 20
    assert _calc_accuracy(20, 1800) == 100.0
    assert _calc_accuracy(0, 10) == 0.0


def test_accuracy_ratio_accepts_fraction_and_percentage_inputs():
    assert _accuracy_ratio(0.75) == 0.75
    assert _accuracy_ratio(75) == 0.75
    assert _accuracy_ratio(125) == 1.0
    assert _accuracy_ratio(None) == 0.0
