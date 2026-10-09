"""Unit tests for the conversions in bin/user/units.py."""

import pytest

from user.units import kmh_to_mps, to_C, to_F, to_in, to_mph, to_v

FUNCS = [to_F, to_C, to_mph, to_in, to_v, kmh_to_mps]


@pytest.mark.parametrize(
    ('func', 'value', 'expected'),
    [
        # to_F: Celsius -> Fahrenheit
        (to_F, 0, 32.0),
        (to_F, 100, 212.0),
        (to_F, -40, -40.0),
        (to_F, 37, 98.6),
        # to_C: Fahrenheit -> Celsius
        (to_C, 32, 0.0),
        (to_C, 212, 100.0),
        (to_C, -40, -40.0),
        (to_C, 98.6, 37.0),
        # to_mph: km/h -> mph
        (to_mph, 0, 0.0),
        (to_mph, 1, 0.621371),
        (to_mph, 100, 62.1371),
        # to_in: mm -> inches
        (to_in, 0, 0.0),
        (to_in, 25.4, 1.0),
        (to_in, 2.54, 0.1),
        # to_v: millivolts -> volts
        (to_v, 0, 0.0),
        (to_v, 1000, 1.0),
        (to_v, 500, 0.5),
        # kmh_to_mps: km/h -> m/s
        (kmh_to_mps, 0, 0.0),
        (kmh_to_mps, 3.6, 1.0),
        (kmh_to_mps, 36, 10.0),
    ],
)
def test_conversion(func, value, expected):
    assert func(value) == pytest.approx(expected)


@pytest.mark.parametrize('func', FUNCS)
def test_none_is_passed_through(func):
    assert func(None) is None
