"""Plain math helpers, no UI in here."""
import math


def validate_number(value, name="value"):
    """Turn input into a finite float, or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError(f"{name} is empty")
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite")
    return v


def polar_to_cartesian(r, theta_deg):
    r = validate_number(r, "distance")
    t = validate_number(theta_deg, "angle")
    rad = math.radians(t % 360.0)
    x, y = r * math.cos(rad), r * math.sin(rad)
    # snap exact quadrants so cos(90) isn't 6e-17
    m = t % 360.0
    if m == 0.0:
        x, y = r, 0.0
    elif m == 90.0:
        x, y = 0.0, r
    elif m == 180.0:
        x, y = -r, 0.0
    elif m == 270.0:
        x, y = 0.0, -r
    return x, y


def distance(x, y):
    return math.hypot(x, y)


def angle_deg(x, y):
    """Angle in [0, 360); 0 at the origin."""
    if x == 0 and y == 0:
        return 0.0
    return math.degrees(math.atan2(y, x)) % 360.0
