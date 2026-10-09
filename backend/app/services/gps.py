"""Read EXIF GPS; validate coordinates; report gps_source (TRD 4.4)."""
from PIL import Image

GPS_IFD = 0x8825
GPS_SOURCES = ("exif", "manual", "map_click")


def exif_gps(img: Image.Image) -> tuple[float, float] | None:
    """(lat, lng) from the photo's EXIF, or None if it has no usable GPS."""
    try:
        gps = img.getexif().get_ifd(GPS_IFD)
        lat = _degrees(gps[2], gps.get(1, "N"), "S")
        lng = _degrees(gps[4], gps.get(3, "E"), "W")
    except (KeyError, TypeError, ValueError, ZeroDivisionError, IndexError):
        return None
    if valid(lat, lng) and (lat, lng) != (0.0, 0.0):  # 0,0 is what some phones write when they had no fix
        return lat, lng
    return None


def _degrees(dms, ref: str, negative_ref: str) -> float:
    d, m, s = (float(x) for x in dms)
    value = d + m / 60 + s / 3600
    return -value if str(ref).upper().startswith(negative_ref) else value


def valid(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180
