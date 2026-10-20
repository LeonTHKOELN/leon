"""Geometrie: Entfernungen und Stützpunkte entlang der Route."""
import math

EARTH_R = 6_371_000  # mittlerer Erdradius in m


def haversine_m(lat1, lon1, lat2, lon2):
    """Großkreisentfernung zwischen zwei Koordinaten in Metern."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def sample_route(start, ziel, raster_m, max_points=600):
    """Gleichabständige Stützpunkte von Start bis Ziel (inkl. beider Endpunkte).

    Für kurze Strecken (wenige km) ist die lineare Interpolation der Koordinaten
    praktisch identisch mit dem Großkreis.
    """
    dist = haversine_m(*start, *ziel)
    n = max(1, math.ceil(dist / max(raster_m, 1.0)))
    n = min(n, max_points)
    pts = [(start[0] + (ziel[0] - start[0]) * i / n, start[1] + (ziel[1] - start[1]) * i / n)
           for i in range(n + 1)]
    ds = [dist * i / n for i in range(n + 1)]
    return dist, pts, ds, dist / n
