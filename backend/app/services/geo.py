"""Haversine distance helper used by matching, zones, planner."""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))
