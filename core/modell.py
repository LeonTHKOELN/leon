"""Gesamtrechnung: verbindet Profil, Packen, Anreise und Kosten zu einem Ergebnis.

Use Cases
  Forst      Geräte und Material zum Arbeitsplatz am Hang, optional abends zurück.
  Heuernte   Mähtag(e), Trocknung, Erntetag(e) mit Heuflügen ins Tal (siehe core/heu.py).
"""
import math

from . import heu, kosten, packen
from .fmt import de
from .trace import Trace

USE_CASES = ["Forst", "Heuernte"]


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


def berechne(job, p, prof, geraete, anreise, heli_basis, optionen=(), wiese=None):
    opts = list(optionen) or [anreise]
    at = anreise_trace(opts, anreise, heli_basis)
    if job.get("usecase") == "Heuernte" and wiese:
        return _heuernte(job, p, prof, geraete, anreise, heli_basis, opts, wiese, at)
    return _forst(job, p, prof, geraete, anreise, heli_basis, opts, at)


def _forst(job, p, prof, geraete, anreise, hb, opts, at):
    pk = packen.pack(job, p, geraete)
    n, tage, rueck = len(pk["flights"]), max(1, job["tage"]), bool(job["rueck"])
    d = kosten.drohne(prof, p, anreise, [{
        "name": "Einsatztag", "anzahl": tage, "fluege": n * (2 if rueck else 1),
        "modus": "geraete" if rueck else "einfach", "warte_h": job["dauer_h"]}])
    h = kosten.heli(pk["brutto"], tage * (2 if rueck else 1), p, hb,
                    "Je Einsatztag ein Anflug für den Hintransport, bei Rücktransport ein zweiter.")
    laeufe = [{"name": "Ausrüstung hoch", "kg": pk["netto"], "traglast": p["manuell.traglast_kg"],
               "richtung": "hoch", "anzahl": tage}]
    if rueck:
        laeufe.append({"name": "Ausrüstung runter", "kg": pk["netto"], "traglast": p["manuell.traglast_kg"],
                       "richtung": "runter", "anzahl": tage})
    m = kosten.manuell(prof, p, job["team"], laeufe)
    return {"usecase": "Forst", "P": prof, "pack": pk, "packs": [("Einsatztag", pk)], "drohne": d, "heli": h,
            "manuell": m, "anreise": anreise, "heli_basis": hb, "optionen": opts, "heu": None,
            "has_dg": pk["has_dg"], "too_heavy": pk["too_heavy"],
            "traces": [prof["trace"], pk["trace"], at, d["trace"], h["trace"], m["trace"]]}


def _heuernte(job, p, prof, geraete, anreise, hb, opts, wiese, at):
    team = job["team"]
    energie = packen.energie_items(job, p)
    verpflegung = packen.geraete_items({"wv": 1}, p, geraete)
    tag1 = packen.geraete_items({"fs": team}, p, geraete) + energie + verpflegung
    saecke = [{"name": "Heusammelsack (leer)", "kg": p["sack.leergewicht_kg"], "dg": False}
              for _ in range(int(p["sack.anzahl"]))]
    tag3 = packen.geraete_items({"lb": team}, p, geraete) + saecke + energie + verpflegung
    pk1 = packen.pack_items(tag1, p, job, "Packen Mähtag")
    pk3 = packen.pack_items(tag3, p, job, "Packen Erntetag")
    t_um = kosten.umlauf(prof, p)
    H = heu.heuernte(p, job, wiese, t_um)
    if not H["ok"]:
        return {**_forst(job, p, prof, geraete, anreise, hb, opts, at), "usecase": "Heuernte", "heu": H}

    mt, et = H["maeh_tage"], H["ernte_tage"]
    heufluege_tag = math.ceil(H["fluege"] / et)
    d = kosten.drohne(prof, p, anreise, [
        {"name": "Mähtag", "anzahl": mt, "fluege": 2 * len(pk1["flights"]), "modus": "geraete",
         "warte_h": H["maeh_h"] / mt},
        {"name": "Erntetag", "anzahl": et, "fluege": 2 * len(pk3["flights"]) + heufluege_tag, "modus": "dauer",
         "praesenz_h": H["ernte_h"] / et},
    ])
    traglast = p["manuell.traglast_kg"]
    geraete_laeufe = [
        {"name": "Mähgeräte hoch", "kg": pk1["netto"], "traglast": traglast, "richtung": "hoch", "anzahl": mt},
        {"name": "Mähgeräte runter", "kg": pk1["netto"], "traglast": traglast, "richtung": "runter", "anzahl": mt},
        {"name": "Erntegeräte hoch", "kg": pk3["netto"], "traglast": traglast, "richtung": "hoch", "anzahl": et},
        {"name": "Erntegeräte runter", "kg": pk3["netto"], "traglast": traglast, "richtung": "runter", "anzahl": et},
    ]
    g = kosten.manuell(prof, p, team, geraete_laeufe, "Geräte tragen (Heli-Variante)")
    heu_brutto = H["fuellungen"] * (H["je_sack"] + p["sack.leergewicht_kg"])
    h = kosten.heli(heu_brutto / et, et, p, hb,
                    "Der Heli fliegt nur das Heu (alle Säcke bzw. Netze vorbereitet), die Geräte trägt das Team.",
                    zusatz=[("Geräte tragen (Team)", g["Kosten (€)"], g["Zeit (min)"])])
    m = kosten.manuell(prof, p, team, geraete_laeufe + [
        {"name": "Heu ins Tal", "kg": H["heu_kg"], "traglast": p["manuell.traglast_heu_kg"], "richtung": "runter",
         "anzahl": 1}])
    return {"usecase": "Heuernte", "P": prof, "pack": pk1, "packs": [("Mähtag", pk1), ("Erntetag", pk3)],
            "drohne": d, "heli": h, "manuell": m, "anreise": anreise, "heli_basis": hb, "optionen": opts, "heu": H,
            "has_dg": pk1["has_dg"] or pk3["has_dg"], "too_heavy": pk1["too_heavy"] + pk3["too_heavy"],
            "traces": [prof["trace"], H["trace"], pk1["trace"], pk3["trace"], at, d["trace"], h["trace"],
                       m["trace"]]}
