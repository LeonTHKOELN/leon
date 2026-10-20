"""Sitzungszustand: Auftragsdaten (w_*), Parameterwerte (p.*) und deren Metadaten (m.*).

- w_<name>   Eingaben der Planungsseiten (Koordinaten, Stückzahlen, Team …)
- p.<key>    aktueller Wert eines Parameters aus config/parameter.yaml
- m.<key>    Status, Quelle und Kommentar eines Parameters (in der App änderbar)
"""
import re

import streamlit as st

from core import geo, hoehe, modell, profil
from core import params as registry

S = st.session_state

PLAN_PAGES = [  # Reihenfolge der Planungsschritte (Stepper und Weiter/Zurück)
    ("views/projekt.py", "Projekt & Route"),
    ("views/equipment.py", "Equipment"),
    ("views/flugplan.py", "Flugplan"),
    ("views/wirtschaftlichkeit.py", "Wirtschaftlichkeit"),
]

JOB_DEFAULTS = {
    "w_einsatz": "Hangpflege Silbertal",
    "w_start_name": "Landeplatz Tal",
    "w_start_lat": 47.0800, "w_start_lon": 9.9170, "w_start_alt": 920,
    "w_ziel_lat": 47.0890, "w_ziel_lon": 9.9330, "w_ziel_alt": 1340,
    "w_alt_manual": False, "w_start_paste": "", "w_ziel_paste": "",
    "w_dauer": 8, "w_team": 2,
    "w_energie": "Akku-Lösung", "w_akkus": 6, "w_liter": 5.0,
    "w_q_ms": 1, "w_q_fs": 1, "w_q_eb": 1, "w_q_ht": 0, "w_q_sw": 0, "w_q_zb": 1, "w_q_wz": 0, "w_q_wv": 1,
}
EXPORT_JOB_KEYS = [k for k in JOB_DEFAULTS if not k.endswith("_paste")]


@st.cache_resource
def load_config():
    params, gruppen = registry.load_registry()
    return params, gruppen, registry.load_scenarios()


REG, GRUPPEN, SZENARIEN = load_config()
GERAETE = {k.split(".", 1)[1]: REG[k].label for g in GRUPPEN if g.id == "geraete" for k in g.keys}


def meta_default(k):
    p = REG[k]
    return {"status": p.status, "quelle": p.quelle, "kommentar": p.kommentar}


def init():
    for k, v in JOB_DEFAULTS.items():
        S.setdefault(k, v)
    for k, p in REG.items():
        S.setdefault(f"p.{k}", p.wert)
        S.setdefault(f"m.{k}", meta_default(k))
    S.setdefault("szenario", "Basis")
    S.setdefault("ed_ver", 0)
    S.setdefault("pin_mode", "Landeplatz")
    # Widget-Werte über Seitenwechsel erhalten (Streamlit löscht sonst Werte nicht angezeigter Widgets)
    for k in [k for k in S.keys() if str(k).startswith("w_")]:
        S[k] = S[k]
    # Kartenklick aus dem letzten Lauf übernehmen (vor dem Rendern der Widgets)
    if "pending_pin" in S:
        mode, lat, lon = S.pop("pending_pin")
        pre = "start" if mode == "Landeplatz" else "ziel"
        S[f"w_{pre}_lat"], S[f"w_{pre}_lon"] = lat, lon
        S["pin_mode"] = "Einsatzort" if mode == "Landeplatz" else "Landeplatz"


def params() -> dict:
    return {k: S[f"p.{k}"] for k in REG}


def changed_keys() -> list:
    return [k for k, p in REG.items() if S[f"p.{k}"] != p.wert]


def job() -> dict:
    return {
        "einsatz": S.w_einsatz, "start_name": S.w_start_name,
        "start": (S.w_start_lat, S.w_start_lon), "ziel": (S.w_ziel_lat, S.w_ziel_lon),
        "team": int(S.w_team), "dauer_h": int(S.w_dauer),
        "anzahl": {g: int(S.get(f"w_q_{g}", 0)) for g in GERAETE},
        "energie": S.w_energie, "akkus": int(S.w_akkus), "liter": float(S.w_liter),
    }


@st.cache_data(ttl=7 * 24 * 3600, show_spinner="Höhendaten werden geladen …")
def _elevations(coords: tuple):
    return hoehe.fetch_elevations(list(coords))


def build_profile(p, j):
    dist, pts, ds, step_eff = geo.sample_route(j["start"], j["ziel"], p["profil.raster_m"])
    terrain, source, error, real = None, "", "", False
    if not S.w_alt_manual:
        try:
            terrain, source = _elevations(tuple((round(a, 6), round(b, 6)) for a, b in pts))
            real = True
            # Manuelle Felder vorbelegen, damit ein Umschalten auf "manuell" mit den API-Werten startet
            S.w_start_alt, S.w_ziel_alt = int(round(terrain[0])), int(round(terrain[-1]))
        except Exception as e:  # noqa: BLE001
            error = str(e)
    if terrain is None:
        terrain = profil.linear_terrain(ds, S.w_start_alt, S.w_ziel_alt)
        source = "Manuelle Höhen (lineare Verbindung, kein Geländeprofil)"
    return profil.build_profile(j["start"], j["ziel"], dist, pts, ds, step_eff, terrain, source, real, error, p)


def result():
    """Komplette Rechnung für den aktuellen Stand. Wird auf jeder Seite vor den Widgets aufgerufen."""
    p, j = params(), job()
    prof = build_profile(p, j)
    r = modell.berechne(j, p, prof, GERAETE)
    r["job"], r["p"] = j, p
    return r


# ---------- Koordinaten einfügen ----------
COORD_RE = re.compile(r"\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$")


def apply_paste(prefix):
    txt = S[f"w_{prefix}_paste"]
    m = COORD_RE.match(txt or "")
    ok = False
    if m:
        lat, lon = (float(g.replace(",", ".")) for g in m.groups())
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            S[f"w_{prefix}_lat"], S[f"w_{prefix}_lon"] = round(lat, 6), round(lon, 6)
            S[f"w_{prefix}_paste"] = ""
            ok = True
    S[f"paste_err_{prefix}"] = bool(txt) and not ok
