"""Sitzungszustand: Auftragsdaten (w_*), Parameterwerte (p.*) und deren Metadaten (m.*).

- w_<name>   Eingaben der Planungsseiten (Koordinaten, Stückzahlen, Team …)
- p.<key>    aktueller Wert eines Parameters aus config/parameter.yaml
- m.<key>    Status, Quelle und Kommentar eines Parameters (in der App änderbar)
"""
import copy
import re

import streamlit as st

from core import anbieter as anb
from core import geo, heu, hoehe, modell, profil
from core import params as registry
from core.fmt import de as de_

S = st.session_state

PLAN_PAGES = [  # Reihenfolge der Planungsschritte (Stepper und Weiter/Zurück)
    ("views/projekt.py", "Projekt & Route"),
    ("views/anbieter.py", "Anbieter & Anreise"),
    ("views/equipment.py", "Equipment"),
    ("views/arbeitsplanung.py", "Arbeitsplanung"),
    ("views/flugplan.py", "Flugplan"),
    ("views/wirtschaftlichkeit.py", "Wirtschaftlichkeit"),
]

JOB_DEFAULTS = {
    # Beispiel: Landeplatz im Ort Silbertal, Einsatz am Hang Richtung Kristberg (Montafon)
    "w_einsatz": "Hangpflege Kristberg",
    "w_start_name": "Landeplatz Silbertal",
    "w_start_lat": 47.0937, "w_start_lon": 9.9831, "w_start_alt": 886,
    "w_ziel_lat": 47.1000, "w_ziel_lon": 9.9833, "w_ziel_alt": 1167,
    "w_alt_manual": False, "w_start_paste": "", "w_ziel_paste": "",
    "w_dauer": 8, "w_team": 2, "w_tage": 1, "w_rueck": True,
    "w_anbieter": "", "w_heli_basis": "",
    "w_usecase": "Forst",
    # Beispielwiese (ca. 1 ha) am Hang Richtung Kristberg, Eckpunkte (lat, lon)
    "w_wiese": [[47.10045, 9.98264], [47.10050, 9.98390], [47.09958, 9.98400], [47.09950, 9.98270]],
    "w_energie": "Akku-Lösung", "w_akkus": 6, "w_liter": 5.0,
    "w_q_ms": 1, "w_q_fs": 1, "w_q_eb": 1, "w_q_ht": 0, "w_q_sw": 0, "w_q_zb": 1, "w_q_wz": 0, "w_q_wv": 1,
    "w_q_lb": 0,
}
EXPORT_JOB_KEYS = [k for k in JOB_DEFAULTS if not k.endswith("_paste")]


def _stand(*pfade):
    """Änderungszeitpunkt der Dateien: neuer Stand im Repo → Zwischenspeicher wird neu befüllt."""
    return tuple(pf.stat().st_mtime_ns for pf in pfade)


@st.cache_resource
def load_config(_stand_):
    params, gruppen = registry.load_registry()
    return params, gruppen, registry.load_scenarios()


REG, GRUPPEN, SZENARIEN = load_config(_stand(registry.CONFIG / "parameter.yaml", registry.CONFIG / "szenarien.yaml"))
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
    for k in [k for k in S.keys() if str(k).startswith(("p.", "m.")) and str(k)[2:] not in REG]:
        del S[k]  # Parameter, die es im neuen Stand nicht mehr gibt
    S.setdefault("szenario", "Basis")
    S.setdefault("ed_ver", 0)
    S.setdefault("pin_mode", "Landeplatz")
    if "anbieter_liste" not in S:
        S.anbieter_liste = load_anbieter()
    # Widget-Werte über Seitenwechsel erhalten (Streamlit löscht sonst Werte nicht angezeigter Widgets)
    for k in [k for k in S.keys() if str(k).startswith("w_")]:
        S[k] = S[k]
    # Kartenklick aus dem letzten Lauf übernehmen (vor dem Rendern der Widgets)
    if "pending_pin" in S:
        mode, lat, lon = S.pop("pending_pin")
        pre = "start" if mode == "Landeplatz" else "ziel"
        S[f"w_{pre}_lat"], S[f"w_{pre}_lon"] = lat, lon
        S["pin_mode"] = "Einsatzort" if mode == "Landeplatz" else "Landeplatz"
    if "pending_wiese" in S:  # gezeichnete Wiese übernehmen, Einsatzort = Mitte der Wiese
        poly = S.pop("pending_wiese")
        try:
            g = heu.wiese_geometrie([tuple(x) for x in poly])
            S.w_wiese = [list(x) for x in poly]
            S.w_ziel_lat, S.w_ziel_lon = round(g["schwerpunkt"][0], 6), round(g["schwerpunkt"][1], 6)
        except ValueError as e:
            S.wiese_msg = str(e)


@st.cache_data
def _load_anbieter(_stand_):
    return anb.load()


def load_anbieter():
    return _load_anbieter(_stand(anb.DATA))


@st.cache_data(ttl=30 * 24 * 3600, show_spinner="Adresse wird gesucht …")
def _geocode(adresse: str):
    return anb.geocode(adresse)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner="Route wird berechnet …")
def _route(a: tuple, b: tuple):
    return anb.route(a, b)


def anbieter_mit_koordinaten():
    """Anbieterliste mit aufgelösten Koordinaten und Herkunft der Koordinaten."""
    out = []
    for a in S.anbieter_liste:
        a = copy.deepcopy(a)
        if a.get("lat") is not None and a.get("lon") is not None:
            a["koord_quelle"] = "Anbieterliste"
        else:
            try:
                a["lat"], a["lon"] = _geocode(a["adresse"])
                a["koord_quelle"] = "Adresssuche OpenStreetMap"
            except Exception:  # noqa: BLE001
                if a.get("lat_ca") is not None:
                    a["lat"], a["lon"] = a["lat_ca"], a["lon_ca"]
                    a["koord_quelle"] = "ungefähr (Adresssuche nicht erreichbar)"
                else:
                    continue
        out.append(a)
    return out


def anreise_optionen(p, landeplatz, max_routing=3):
    """Drohnen-Anbieter nach Fahrzeit. Die nächsten (Luftlinie) werden per Straßenrouting berechnet."""
    liste = [a for a in anbieter_mit_koordinaten() if a["typ"] == "Drohne"]
    for a in liste:
        a["luft_km"] = anb.luftlinie_km((a["lat"], a["lon"]), landeplatz)
    liste.sort(key=lambda a: a["luft_km"])
    opts = []
    for i, a in enumerate(liste):
        src = (a["lat"], a["lon"])
        r, quelle = None, ""
        if i < max_routing:
            try:
                r = _route(tuple(round(x, 6) for x in src), tuple(round(x, 6) for x in landeplatz))
                quelle = f"Straßenrouting ({r['server']})"
            except Exception:  # noqa: BLE001
                r = None
        if r is None:
            r = anb.fallback_route(src, landeplatz, p)
            quelle = f"Ersatzrechnung Luftlinie × {de_(p['anreise.umwegfaktor'], 2)}"
        opts.append({"anbieter": a, "km": r["km"], "route_min": r["min"], "geometry": r["geometry"],
                     "quelle": quelle, "luft_km": a["luft_km"], "snap_m": r["snap_b_m"]})
    opts.sort(key=lambda o: o["route_min"])
    return opts


def heli_basen(landeplatz):
    liste = [a for a in anbieter_mit_koordinaten() if a["typ"] == "Helikopter"]
    out = [{"anbieter": a, "km": anb.luftlinie_km((a["lat"], a["lon"]), landeplatz)} for a in liste]
    return sorted(out, key=lambda x: x["km"])


KEIN_ANBIETER = {"anbieter": {"id": "", "name": "Kein Anbieter hinterlegt", "typ": "Drohne"},
                 "km": 0.0, "route_min": 0.0, "geometry": [], "quelle": "keine Anreise", "luft_km": 0.0,
                 "snap_m": 0.0}
KEINE_BASIS = {"anbieter": {"id": "", "name": "Keine Heli-Basis hinterlegt", "typ": "Helikopter"}, "km": 0.0}


def params() -> dict:
    return {k: S[f"p.{k}"] for k in REG}


def changed_keys() -> list:
    return [k for k, p in REG.items() if S[f"p.{k}"] != p.wert]


def job() -> dict:
    return {
        "einsatz": S.w_einsatz, "start_name": S.w_start_name,
        "start": (S.w_start_lat, S.w_start_lon), "ziel": (S.w_ziel_lat, S.w_ziel_lon),
        "usecase": S.w_usecase,
        "team": int(S.w_team), "dauer_h": int(S.w_dauer), "tage": int(S.w_tage), "rueck": bool(S.w_rueck),
        "anzahl": {g: int(S.get(f"w_q_{g}", 0)) for g in GERAETE},
        "energie": S.w_energie, "akkus": int(S.w_akkus), "liter": float(S.w_liter),
    }


@st.cache_data(ttl=7 * 24 * 3600, show_spinner="Höhendaten werden geladen …")
def _elevations(coords: tuple):
    return hoehe.fetch_elevations(list(coords))


def wiese_auswerten():
    """Fläche, Schwerpunkt und Hangneigung der gezeichneten Wiese (Höhenraster über die Höhen-API)."""
    poly = [tuple(x) for x in S.w_wiese]
    g = heu.wiese_geometrie(poly)
    pts, xy, abstand = heu.raster_in_wiese(poly)
    try:
        z, quelle = _elevations(tuple((round(a, 6), round(b, 6)) for a, b in pts))
        pct, grad = heu.neigung(xy, z)
        g.update({"neigung_pct": pct, "neigung_grad": grad, "h_min": min(z), "h_max": max(z),
                  "hoehen_quelle": f"{len(pts)} Rasterpunkte, Abstand {round(abstand)} m · {quelle}"})
    except Exception:  # noqa: BLE001
        g.update({"neigung_pct": 0.0, "neigung_grad": 0.0, "h_min": 0.0, "h_max": 0.0,
                  "hoehen_quelle": "Höhendaten nicht erreichbar, Neigung unbekannt"})
    g["raster_m"] = abstand
    return g


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
    wiese = wiese_auswerten() if j["usecase"] == "Heuernte" else None
    if wiese:
        j["ziel"] = tuple(wiese["schwerpunkt"])  # Heu wird in der Mitte der Wiese gesammelt
    prof = build_profile(p, j)
    opts = anreise_optionen(p, j["start"])
    gew = next((o for o in opts if o["anbieter"]["id"] == S.w_anbieter), opts[0] if opts else KEIN_ANBIETER)
    basen = heli_basen(j["start"])
    hb = next((b for b in basen if b["anbieter"]["id"] == S.w_heli_basis), basen[0] if basen else KEINE_BASIS)
    r = modell.berechne(j, p, prof, GERAETE, gew, hb, opts, wiese=wiese)
    r["wiese"] = wiese
    r["heli_basen"] = basen
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
