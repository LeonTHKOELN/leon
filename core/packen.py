"""Packen und Flugeinteilung: Gegenstände → Boxen → Flüge."""
from .fmt import de
from .trace import Trace

ENERGIE_OPTIONEN = ["Akku-Lösung", "Benzin-Lösung", "Beides"]


def first_fit(items, cap, key):
    """First-Fit-Decreasing: schwerste Teile zuerst in die erste Einheit, in die sie passen."""
    bins = []
    for it in sorted(items, key=lambda x: -x[key]):
        for b in bins:
            if b["load"] + it[key] <= cap + 1e-9:
                b["items"].append(it)
                b["load"] += it[key]
                break
        else:
            bins.append({"items": [it], "load": it[key]})
    return bins


def energie_items(job, p):
    """Akkus und Kraftstoff laut Auswahl im Schritt Equipment (Gefahrgut)."""
    items = []
    if job["energie"] in ("Akku-Lösung", "Beides"):
        for _ in range(int(job["akkus"])):
            items.append({"name": "Akku", "kg": p["akku.gewicht_kg"], "dg": True})
    if job["energie"] in ("Benzin-Lösung", "Beides") and job["liter"] > 0:
        kg = job["liter"] * p["kraftstoff.dichte_kg_l"] + p["kanister.leergewicht_kg"]
        items.append({"name": f"Kraftstoff {de(job['liter'], 1)} l", "kg": kg, "dg": True})
    return items


def geraete_items(anzahl, p, geraete):
    """anzahl: {id: Stück}, Gewichte aus den Parametern geraet.<id>."""
    return [{"name": geraete[g], "kg": p[f"geraet.{g}"], "dg": False}
            for g, n in anzahl.items() if g in geraete for _ in range(int(n))]


def build_items(job, p, geraete):
    """Liste aller Einzelteile für den Forst-Einsatz."""
    return geraete_items(job["anzahl"], p, geraete) + energie_items(job, p)


def build_units(items, p):
    """Normale Teile in Boxen, Gefahrgut in Gefahrgut-Boxen, Übergroßes ins Lastnetz."""
    cap = p["box.zuladung_kg"]
    normal = [i for i in items if not i["dg"] and i["kg"] <= cap]
    oversize = [i for i in items if not i["dg"] and i["kg"] > cap]
    dg = [i for i in items if i["dg"]]
    units = []
    for b in first_fit(normal, cap, "kg"):
        units.append({"typ": "Box", "items": b["items"], "netto": b["load"],
                      "brutto": b["load"] + p["box.leergewicht_kg"], "dg": False})
    for b in first_fit(dg, cap, "kg"):
        units.append({"typ": "Gefahrgut-Box", "items": b["items"], "netto": b["load"],
                      "brutto": b["load"] + p["box.gg_leergewicht_kg"], "dg": True})
    for i in oversize:
        units.append({"typ": "Lastnetz", "items": [i], "netto": i["kg"],
                      "brutto": i["kg"] + p["box.netz_leergewicht_kg"], "dg": False})
    for n, u in enumerate(units):
        u["label"] = f"{u['typ']} {chr(65 + n % 26)}"
    return units


def build_flights(units, p):
    cap = p["drohne.nutzlast_kg"]
    too_heavy = [u for u in units if u["brutto"] > cap]
    ok = [u for u in units if u["brutto"] <= cap]
    groups = ([[u for u in ok if not u["dg"]], [u for u in ok if u["dg"]]]
              if p["flug.gefahrgut_separat"] else [ok])
    flights = []
    for g in groups:
        for b in first_fit(g, cap, "brutto"):
            flights.append({"units": b["items"], "load": b["load"]})
    return flights, too_heavy


def pack(job, p, geraete):
    return pack_items(build_items(job, p, geraete), p, job, "Packen und Flugeinteilung")


def pack_items(items, p, job, titel):
    tr = Trace("packen", titel,
               "Gegenstände werden in Transporteinheiten gepackt, die Einheiten anschließend auf Flüge verteilt "
               "(First-Fit-Decreasing).")
    units = build_units(items, p)
    flights, too_heavy = build_flights(units, p)
    netto = sum(i["kg"] for i in items)
    brutto = sum(u["brutto"] for u in units)
    n_dg = sum(1 for i in items if i["dg"])
    tr.add("Nettogewicht Fracht", "Σ Stückzahl × Gewicht je Stück",
           f"{len(items)} Teile, davon {n_dg} Gefahrgut", netto, "kg", 1)
    if job["energie"] in ("Benzin-Lösung", "Beides") and job["liter"] > 0:
        tr.add("Kraftstoff inkl. Kanister", "Liter × Dichte + Kanister",
               f"{de(job['liter'], 1)} l × {de(p['kraftstoff.dichte_kg_l'], 2)} kg/l + "
               f"{de(p['kanister.leergewicht_kg'], 1)} kg",
               job["liter"] * p["kraftstoff.dichte_kg_l"] + p["kanister.leergewicht_kg"], "kg", 1)
    tr.add("Transporteinheiten", "Boxen bis Zuladung, Gefahrgut getrennt, Übergroßes ins Lastnetz",
           f"Zuladung je Box {de(p['box.zuladung_kg'])} kg", len(units), "Einheiten", 0)
    tr.add("Bruttogewicht", "Netto + Σ Leergewichte der Einheiten",
           f"{de(netto, 1)} kg + {de(brutto - netto, 1)} kg", brutto, "kg", 1)
    tr.add("Flüge je Richtung", "Einheiten bis zur Nutzlast je Flug zusammenfassen",
           f"Nutzlast {de(p['drohne.nutzlast_kg'])} kg · Gefahrgut separat: "
           f"{'ja' if p['flug.gefahrgut_separat'] else 'nein'}", len(flights), "Flüge", 0,
           kommentar=(f"{len(too_heavy)} Einheit(en) zu schwer für die Drohne" if too_heavy else ""))
    return {"items": items, "units": units, "flights": flights, "too_heavy": too_heavy,
            "netto": netto, "brutto": brutto, "has_dg": n_dg > 0, "trace": tr}
