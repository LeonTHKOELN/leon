"""Anbieter (Drohnen-Dienstleister, Helikopter-Basen): Liste, Geocoding, Routing.

Datenquelle: data/anbieter.csv. Leere Preisfelder bedeuten: Standardwert aus parameter.yaml verwenden.
Koordinaten: lat/lon, sonst Adresssuche (OpenStreetMap Nominatim), sonst lat_ca/lon_ca (ungefähr).
Routing: OSRM-Demoserver (OpenStreetMap-Straßennetz). Fallback: Luftlinie × Umwegfaktor.
"""
import csv
from pathlib import Path

import requests

from .geo import haversine_m

DATA = Path(__file__).resolve().parent.parent / "data" / "anbieter.csv"
TYPEN = ["Drohne", "Helikopter"]
UA = {"User-Agent": "LiftPlanner/1.0 (Studienprojekt TH Koeln x STIHL)"}
NUM = ["lat", "lon", "lat_ca", "lon_ca", "pauschale_eur", "eur_km", "fahrt_eur_h", "einsatz_eur_h",
       "heli_eur_min", "heli_mindest_min", "heli_bereitstellung_eur"]
SPALTEN = ["id", "name", "typ", "adresse", *NUM[:4], "fiktiv", *NUM[4:], "kommentar"]


def _num(v):
    v = (v or "").strip().replace(",", ".")
    return float(v) if v else None


def load(path: Path = DATA) -> list:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        a = {k: (r.get(k) or "").strip() for k in SPALTEN}
        for k in NUM:
            a[k] = _num(r.get(k))
        a["fiktiv"] = a["fiktiv"].lower() in ("ja", "true", "1", "x")
        if a["typ"] not in TYPEN:
            raise ValueError(f"Anbieter {a['id']}: unbekannter Typ {a['typ']}")
        out.append(a)
    return out


def to_csv(anbieter: list) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SPALTEN, extrasaction="ignore")
    w.writeheader()
    for a in anbieter:
        row = {k: a.get(k) for k in SPALTEN}
        row["fiktiv"] = "ja" if a.get("fiktiv") else "nein"
        w.writerow({k: ("" if v is None else v) for k, v in row.items()})
    return buf.getvalue()


def geocode(adresse: str):
    """Adresse → (lat, lon) über Nominatim. Nutzungsregeln: max. 1 Anfrage/s, Ergebnisse cachen."""
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": adresse, "format": "json", "limit": 1}, headers=UA, timeout=15)
    r.raise_for_status()
    js = r.json()
    if not js:
        raise ValueError(f"Adresse nicht gefunden: {adresse}")
    return float(js[0]["lat"]), float(js[0]["lon"])


def route(a, b):
    """Straßenroute a → b (je (lat, lon)). Rückgabe km, min, Geometrie [(lat, lon), …]."""
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{a[1]:.6f},{a[0]:.6f};{b[1]:.6f},{b[0]:.6f}")
    r = requests.get(url, params={"overview": "simplified", "geometries": "geojson"}, headers=UA, timeout=15)
    r.raise_for_status()
    js = r.json()
    if js.get("code") != "Ok" or not js.get("routes"):
        raise ValueError(js.get("message", "keine Route gefunden"))
    rt = js["routes"][0]
    return {"km": rt["distance"] / 1000, "min": rt["duration"] / 60,
            "geometry": [(c[1], c[0]) for c in rt["geometry"]["coordinates"]]}


def luftlinie_km(a, b):
    return haversine_m(a[0], a[1], b[0], b[1]) / 1000


def fallback_route(a, b, p):
    km = luftlinie_km(a, b) * p["anreise.umwegfaktor"]
    return {"km": km, "min": km / p["anreise.v_kmh"] * 60, "geometry": [a, b]}
