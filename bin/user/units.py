# utilities for inline unit conversions.  respect the None!
def to_F(v: int | float | None) -> float | None:
    if v is not None:
        v = v * 1.8 + 32
    return v


def to_C(v: int | float | None) -> float | None:
    if v is not None:
        v = 5 / 9 * (v - 32)
    return v


def to_mph(v: int | float | None) -> float | None:
    if v is not None:
        v *= 0.621371
    return v


def to_in(v: int | float | None) -> float | None:
    if v is not None:
        v /= 25.4
    return v


def to_v(v: int | float | None) -> float | None:
    if v is not None:
        v /= 1000
    return v


def kmh_to_mps(v: int | float | None) -> float | None:
    if v is not None:
        v /= 3.6
    return v
