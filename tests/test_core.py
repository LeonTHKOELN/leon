"""Tests für den Rechenkern (ohne Netzwerk, mit synthetischem Gelände).

Ausführen im Projektordner:  python -m pytest -q
"""
import math

import pytest

from core import geo, modell, packen, profil
from core import params as registry

REG, GRUPPEN = registry.load_registry()
GERAETE = {k.split(".", 1)[1]: REG[k].label for g in GRUPPEN if g.id == "geraete" for k in g.keys}
JOB = {"einsatz": "Test", "start_name": "Start", "start": (47.0800, 9.9170), "ziel": (47.0890, 9.9330),
       "team": 2, "dauer_h": 8, "anzahl": {"ms": 1, "fs": 1, "eb": 1, "zb": 1, "wv": 1},
       "energie": "Akku-Lösung", "akkus": 6, "liter": 5.0, "tage": 1, "rueck": False}
ANREISE = {"anbieter": {"id": "x", "name": "Test-Anbieter", "fiktiv": True}, "km": 20.0, "route_min": 30.0,
           "geometry": [], "quelle": "Test", "luft_km": 15.0}
BASIS = {"anbieter": {"id": "h", "name": "Test-Basis"}, "km": 30.0}


def run(p=None, job=None, terrain_fn=None):
    p = p or registry.defaults(REG)
    job = job or JOB
    dist, pts, ds, step = geo.sample_route(job["start"], job["ziel"], p["profil.raster_m"])
    terrain = [terrain_fn(d) for d in ds] if terrain_fn else profil.linear_terrain(ds, 900, 1300)
    prof = profil.build_profile(job["start"], job["ziel"], dist, pts, ds, step, terrain, "Test", True, "", p)
    return modell.berechne(job, p, prof, GERAETE, ANREISE, BASIS)


def test_registry_valid():
    assert len(REG) > 30
    for k, prm in REG.items():
        assert prm.status in registry.STATUS
        if prm.typ != "bool" and prm.min is not None:
            assert prm.min <= prm.wert <= prm.max, k


def test_scenarios_only_known_keys():
    for sc in registry.load_scenarios():
        registry.scenario_values(REG, sc)  # wirft bei unbekannten Keys


def test_haversine_known_distance():
    # 1 Breitengrad ≈ 111,2 km
    assert geo.haversine_m(47, 10, 48, 10) == pytest.approx(111_195, rel=1e-3)


def test_sampling_spacing():
    dist, pts, ds, step = geo.sample_route((47.08, 9.917), (47.089, 9.933), 30)
    assert step <= 30 and len(pts) == len(ds) and ds[-1] == pytest.approx(dist)


def test_flat_route_direct_flight():
    r = run(terrain_fn=lambda d: 1000.0)
    P = r["P"]
    assert P["direct_min_agl"] == pytest.approx(P["clear"])
    assert P["flight_len"] == pytest.approx(P["dist"] + 2 * P["clear"])


def test_path_stays_in_corridor():
    r = run(terrain_fn=lambda d: 900 + 0.3 * d + 80 * math.sin(d / 120))
    P = r["P"]
    for t, h in zip(P["terrain"], P["path"]):
        assert P["clear"] - 1e-6 <= h - t <= P["ceiling"] + 1e-6


def test_flight_time_limited_by_climb():
    p = registry.defaults(REG)
    p["drohne.steigrate_ms"] = 0.5   # sehr langsames Steigen → Hinflug bergauf dauert länger als Rückflug
    r = run(p=p)
    assert r["P"]["out_min"] > r["P"]["back_min"]


def test_dangerous_goods_separate_flights():
    p = registry.defaults(REG)
    pk = packen.pack(JOB, p, GERAETE)
    assert any(all(u["dg"] for u in f["units"]) for f in pk["flights"])
    assert not any(any(u["dg"] for u in f["units"]) and any(not u["dg"] for u in f["units"])
                   for f in pk["flights"])


def test_flights_respect_payload():
    p = registry.defaults(REG)
    p["drohne.nutzlast_kg"] = 40
    pk = packen.pack(JOB, p, GERAETE)
    assert all(f["load"] <= 40 + 1e-9 for f in pk["flights"])


def test_heli_formula():
    p = registry.defaults(REG)
    r = run(p=p)
    rot = math.ceil(r["pack"]["brutto"] / p["heli.nutzlast_kg"])
    minuten = 2 * BASIS["km"] / p["heli.v_kmh"] * 60 + rot * p["heli.rotation_min"]
    erwartet = max(minuten, p["heli.mindest_min"]) * p["heli.eur_min"] + p["heli.bereitstellung_eur"]
    assert r["heli"]["Kosten (€)"] == pytest.approx(erwartet)


def test_heli_minimum_billing():
    p = registry.defaults(REG)
    p["heli.mindest_min"] = 300
    r = run(p=p)
    assert r["heli"]["Kosten (€)"] == pytest.approx(300 * p["heli.eur_min"] + p["heli.bereitstellung_eur"])


def test_drone_dienstleister_formula():
    p = registry.defaults(REG)
    r = run(p=p)
    d, n = r["drohne"], r["drohne"]["fluege"]
    fahrt_h = (ANREISE["route_min"] + p["anreise.zuschlag_min"]) / 60
    personen = 1 + p["personal.helfer_n"]
    anreise = (p["anreise.pauschale_eur"] + 2 * ANREISE["km"] * p["anreise.eur_km"]
               + 2 * fahrt_h * p["dl.fahrt_eur_h"] * personen)
    ruest = (p["einsatz.aufbau_min"] + p["einsatz.abbau_min"]) / 60 * p["dl.einsatz_eur_h"]
    flug = n * d["umlauf_min"] / 60 * p["dl.einsatz_eur_h"]
    assert d["Kosten (€)"] == pytest.approx(anreise + ruest + flug)
    assert d["fix"] + d["variabel"] == pytest.approx(d["Kosten (€)"])


def test_pilot_zero_reduces_cost_in_eigenbetrieb():
    p = registry.defaults(REG)
    p["modell.dienstleister"] = False
    a = run(p=p)["drohne"]["Kosten (€)"]
    p["personal.pilot_eur_h"] = 0
    b = run(p=p)["drohne"]["Kosten (€)"]
    assert b < a


def test_autonomous_has_no_pilot_but_supervision():
    p = registry.defaults(REG)
    p.update({"modell.dienstleister": False, "modell.autonom": True})
    tr = run(p=p)["drohne"]["trace"]
    titel = [s.titel for s in tr.steps]
    assert any("Fernüberwachung" in t for t in titel)
    assert any("kein Pilot" in s.formel for s in tr.steps)


def test_rueck_chooses_cheaper_variant():
    p = registry.defaults(REG)
    job = {**JOB, "rueck": True}
    d = run(p=p, job=job)["drohne"]
    titel = [s.titel for s in d["trace"].steps]
    assert "bleibt vor Ort" in d["variante"] or "zweite Anfahrt" in d["variante"]
    assert any("Variante bleibt vor Ort" in t for t in titel) and any("Variante zweite Anfahrt" in t for t in titel)


def test_days_scale_costs():
    p = registry.defaults(REG)
    one = run(p=p)
    three = run(p=p, job={**JOB, "tage": 3})
    for k in ("drohne", "heli", "manuell"):
        assert three[k]["Kosten (€)"] == pytest.approx(3 * one[k]["Kosten (€)"])


def test_every_trace_has_steps():
    r = run()
    assert all(tr.steps for tr in r["traces"])


def test_anbieter_csv_loads():
    from core import anbieter
    liste = anbieter.load()
    typen = {a["typ"] for a in liste}
    assert {"Drohne", "Helikopter"} <= typen
    assert all(a["name"] and a["adresse"] for a in liste)
    assert anbieter.load.__module__  # CSV-Export und erneutes Laden bleiben gleich
    import tempfile, pathlib
    tmp = pathlib.Path(tempfile.mkdtemp()) / "a.csv"
    tmp.write_text(anbieter.to_csv(liste), encoding="utf-8")
    assert [a["id"] for a in anbieter.load(tmp)] == [a["id"] for a in liste]


def test_din33466_flat_and_steep():
    from core.kosten import _din33466
    p = registry.defaults(REG)
    t, th, tv = _din33466(4.0, 0, 0, p)          # 4 km eben bei 4 km/h → 1 h
    assert t == pytest.approx(1.0)
    t, th, tv = _din33466(1.0, 600, 0, p)        # 600 Hm → 2 h vertikal, 0,25 h horizontal → 2,125 h
    assert t == pytest.approx(2.0 + 0.25 / 2)


def test_drone_co2_includes_vehicle():
    p = registry.defaults(REG)
    a = run(p=p)["drohne"]["CO₂ (kg)"]
    p["co2.fahrzeug_kg_km"] = 0
    b = run(p=p)["drohne"]["CO₂ (kg)"]
    assert a - b == pytest.approx(2 * ANREISE["km"] * 0.25)


# ---------------------------------------------------------------------------
# Heuernte
# ---------------------------------------------------------------------------
from core import heu  # noqa: E402

WIESE = [(47.10045, 9.98264), (47.10050, 9.98390), (47.09958, 9.98400), (47.09950, 9.98270)]


def test_wiese_flaeche_rechteck():
    # 100 m × 100 m Quadrat → 1 ha
    lat0, lon0 = 47.1, 9.98
    dlat = 100 / 111_195
    dlon = 100 / (111_195 * math.cos(math.radians(lat0)))
    g = heu.wiese_geometrie([(lat0, lon0), (lat0, lon0 + dlon), (lat0 + dlat, lon0 + dlon), (lat0 + dlat, lon0)])
    assert g["flaeche_m2"] == pytest.approx(10_000, rel=0.01)


def test_neigung_ebene():
    # Ebene mit 50 % Steigung in y-Richtung
    xy = [(x, y) for x in range(0, 100, 10) for y in range(0, 100, 10)]
    z = [0.5 * y for _, y in xy]
    pct, grad = heu.neigung(xy, z)
    assert pct == pytest.approx(50) and grad == pytest.approx(math.degrees(math.atan(0.5)))


def test_raster_liegt_in_wiese():
    pts, xy, abstand = heu.raster_in_wiese(WIESE)
    assert 3 <= len(pts) <= 200


def _heu_run(p=None, job=None):
    p = p or registry.defaults(REG)
    job = {**JOB, "usecase": "Heuernte", **(job or {})}
    g = heu.wiese_geometrie(WIESE)
    g.update({"neigung_pct": 40, "neigung_grad": 21.8, "h_min": 1100, "h_max": 1180, "hoehen_quelle": "Test"})
    dist, pts, ds, step = geo.sample_route(job["start"], g["schwerpunkt"], p["profil.raster_m"])
    prof = profil.build_profile(job["start"], g["schwerpunkt"], dist, pts, ds, step,
                                profil.linear_terrain(ds, 900, 1150), "Test", True, "", p)
    return modell.berechne(job, p, prof, GERAETE, ANREISE, BASIS, wiese=g), p


def test_heu_flights_match_document_example():
    # Projektdokument: 1 ha, 2.000 kg/ha, 70 kg je Flug → 29 Lastflüge
    p = registry.defaults(REG)
    p.update({"heu.ertrag_kg_ha": 2000, "sack.volumen_m3": 1.0, "heu.dichte_kg_m3": 70})
    r, _ = _heu_run(p)
    H = r["heu"]
    assert H["je_sack"] == pytest.approx(70)
    assert H["fluege"] == math.ceil(H["heu_kg"] / 70)


def test_heu_payload_limit():
    p = registry.defaults(REG)
    p.update({"sack.volumen_m3": 3.0, "heu.dichte_kg_m3": 70})  # 210 kg Volumen > Nutzlast
    r, _ = _heu_run(p)
    assert r["heu"]["je_sack"] == pytest.approx(p["drohne.nutzlast_kg"] - p["sack.leergewicht_kg"])


def test_heu_parallel_needs_enough_sacks():
    p = registry.defaults(REG)
    p["sack.anzahl"] = 1
    seriell = _heu_run(p)[0]["heu"]
    p["sack.anzahl"] = 6
    parallel = _heu_run(p)[0]["heu"]
    assert not seriell["parallel"] and parallel["parallel"]
    assert seriell["ernte_h"] > parallel["ernte_h"]


def test_heu_cost_structure():
    r, p = _heu_run()
    tage = {x["Einsatztag"] for x in r["drohne"]["positionen"]}
    assert tage == {"Mähtag", "Erntetag"}
    assert r["heli"]["Kosten (€)"] > 0 and r["manuell"]["Kosten (€)"] > 0
    assert any("Heu ins Tal" == s.titel for s in r["manuell"]["trace"].steps)
