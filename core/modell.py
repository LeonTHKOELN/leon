"""Gesamtrechnung: verbindet Profil, Packen und Kosten zu einem Ergebnis."""
from . import kosten, packen


def berechne(job, p, prof, geraete):
    pk = packen.pack(job, p, geraete)
    d = kosten.drohne(prof, pk, p)
    h = kosten.heli(pk, p)
    m = kosten.manuell(prof, pk, job, p)
    return {
        "P": prof, "pack": pk, "drohne": d, "heli": h, "manuell": m,
        "traces": [prof["trace"], pk["trace"], d["trace"], h["trace"], m["trace"]],
    }
