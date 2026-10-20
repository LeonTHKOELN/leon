"""Gesamtrechnung: verbindet Profil, Packen, Anreise und Kosten zu einem Ergebnis."""
from . import kosten, packen
from .fmt import de
from .trace import Trace


def anreise_trace(optionen, gewaehlt, heli_basis):
    tr = Trace("anreise", "Anbieter und Anreise",
               "Drohnen-Anbieter werden nach Fahrzeit zum Landeplatz sortiert (Straßenrouting, sonst Luftlinie × "
               "Umwegfaktor). Für den Helikopter zählt die Luftlinie von der Basis.")
    for o in optionen:
        tr.add(o["anbieter"]["name"] + (" (gewählt)" if o is gewaehlt else ""),
               "Route Anbieter → Landeplatz", f"{o['quelle']} · Luftlinie {de(o['luft_km'], 1)} km", 0,
               text=f"{de(o['km'], 1)} km · {de(o['route_min'])} min")
    if heli_basis:
        tr.add(heli_basis["anbieter"]["name"], "Luftlinie Basis → Landeplatz",
               "Koordinaten: " + heli_basis["anbieter"].get("koord_quelle", ""), heli_basis["km"], "km", 1)
    return tr


def berechne(job, p, prof, geraete, anreise, heli_basis, optionen=()):
    pk = packen.pack(job, p, geraete)
    d = kosten.drohne(prof, pk, p, job, anreise)
    h = kosten.heli(pk, p, job, heli_basis)
    m = kosten.manuell(prof, pk, job, p)
    at = anreise_trace(list(optionen) or [anreise], anreise, heli_basis)
    return {
        "P": prof, "pack": pk, "drohne": d, "heli": h, "manuell": m, "anreise": anreise, "heli_basis": heli_basis,
        "optionen": list(optionen) or [anreise],
        "traces": [prof["trace"], pk["trace"], at, d["trace"], h["trace"], m["trace"]],
    }
