"""Geländehöhen aus öffentlichen Höhenmodellen.

1. OpenTopoData, Datensatz EU-DEM 25 m (Europa). Limit: 100 Punkte je Anfrage, 1 Anfrage/s.
2. Fallback Open-Meteo, Copernicus DEM GLO-90 (weltweit). Limit: 100 Punkte je Anfrage.
Wirft RuntimeError, wenn beide Quellen scheitern.
"""
import time

import requests

CHUNK = 100
SRC_EUDEM = "EU-DEM 25 m · OpenTopoData"
SRC_COP = "Copernicus GLO-90 · Open-Meteo"


def _chunks(coords):
    return [coords[i:i + CHUNK] for i in range(0, len(coords), CHUNK)]


def _opentopodata(coords):
    out = []
    for n, chunk in enumerate(_chunks(coords)):
        if n:
            time.sleep(1.05)
        r = requests.get("https://api.opentopodata.org/v1/eudem25m",
                         params={"locations": "|".join(f"{a:.6f},{b:.6f}" for a, b in chunk),
                                 "interpolation": "bilinear"}, timeout=20)
        r.raise_for_status()
        js = r.json()
        if js.get("status") != "OK":
            raise ValueError(js.get("error", "Status nicht OK"))
        vals = [x.get("elevation") for x in js["results"]]
        if any(v is None for v in vals):
            raise ValueError("Punkt außerhalb EU-DEM")
        out += vals
    return out


def _open_meteo(coords):
    out = []
    for chunk in _chunks(coords):
        r = requests.get("https://api.open-meteo.com/v1/elevation",
                         params={"latitude": ",".join(f"{a:.6f}" for a, _ in chunk),
                                 "longitude": ",".join(f"{b:.6f}" for _, b in chunk)}, timeout=20)
        r.raise_for_status()
        vals = r.json()["elevation"]
        if len(vals) != len(chunk) or any(v is None for v in vals):
            raise ValueError("unvollständige Antwort")
        out += vals
    return out


def fetch_elevations(coords):
    errors = []
    for fn, name in [(_opentopodata, SRC_EUDEM), (_open_meteo, SRC_COP)]:
        try:
            return [float(v) for v in fn(coords)], name
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    raise RuntimeError(" | ".join(errors))
