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
       "energie": "Akku-Lösung", "akkus": 6, "liter": 5.0}


def run(p=None, job=None, terrain_fn=None):
    p = p or registry.defaults(REG)
    job = job or JOB
    dist, pts, ds, step = geo.sample_route(job["start"], job["ziel"], p["profil.raster_m"])
    terrain = [terrain_fn(d) for d in ds] if terrain_fn else profil.linear_terrain(ds, 900, 1300)
    prof = profil.build_profile(job["start"], job["ziel"], dist, pts, ds, step, terrain, "Test", True, "", p)
    return modell.berechne(job, p, prof, GERAETE)


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


def test_costs_follow_formulas():
    p = registry.defaults(REG)
    r = run(p=p)
    n = r["drohne"]["fluege"]
    assert r["drohne"]["Kosten (€)"] == pytest.approx(p["drohne.pauschale_eur"] + n * p["drohne.kosten_flug_eur"])
    rot = math.ceil(r["pack"]["brutto"] / p["heli.nutzlast_kg"])
    assert r["heli"]["Kosten (€)"] == pytest.approx((p["heli.anflug_min"] + rot * p["heli.rotation_min"]) * p["heli.eur_min"])


def test_every_trace_has_steps():
    r = run()
    assert all(tr.steps for tr in r["traces"])
