"""Analyse: Sensitivität, Break-even und Szenariovergleich.

Alle Auswertungen rechnen das komplette Modell mit veränderten Parametern neu. Geländeprofil, Route,
Anbieter und Wiese bleiben dabei fest (sie hängen nicht von den Parametern ab), damit keine erneuten
API-Abfragen nötig sind. Ausnahme: der Rasterabstand der Höhenabfrage wird nicht variiert.
"""
from . import modell, profil
from . import params as registry

METHODEN = ["Drohne", "Helikopter", "Tragen"]
ZIELE = {
    "Kosten Drohne": "Kosten der Drohne für den Einsatz",
    "Kosten Helikopter": "Kosten des Helikopters für den Einsatz",
    "Kosten Tragen": "Kosten des manuellen Transports",
    "Kostenvorteil Drohne": "Günstigste Alternative minus Drohne (positiv = Drohne günstiger)",
}
NICHT_VARIIEREN = {"profil.raster_m"}
FLAECHE = "__flaeche_ha"


def neu_rechnen(R, p, wiese=None):
    """Modell mit Parametern p neu rechnen. R ist ein bestehendes Ergebnis (liefert Gelände, Route, Anbieter)."""
    P, j = R["P"], R["job"]
    prof = profil.build_profile(j["start"], j["ziel"], P["dist"], P["pts"], P["ds"], P["step_eff"], P["terrain"],
                                P["source"], P["real"], P["error"], p)
    return modell.berechne(j, p, prof, R["geraete"], R["anreise"], R["heli_basis"], R["optionen"],
                           wiese=wiese if wiese is not None else R.get("wiese"))


def kosten(r):
    return {"Drohne": r["drohne"]["Kosten (€)"], "Helikopter": r["heli"]["Kosten (€)"],
            "Tragen": r["manuell"]["Kosten (€)"]}


def guenstigstes(r):
    k = kosten(r)
    m = min(k, key=k.get)
    return m, k


def zielwert(r, ziel):
    k = kosten(r)
    if ziel == "Kostenvorteil Drohne":
        return min(k["Helikopter"], k["Tragen"]) - k["Drohne"]
    return k[ziel.replace("Kosten ", "")]


def sensitivitaet(R, reg, ziel="Kosten Drohne", delta=0.2):
    """Jeden Zahlenparameter einzeln um ±delta verändern. Rückgabe nach Wirkung sortiert."""
    p = R["p"]
    basis = zielwert(R, ziel)
    rows = []
    for k, prm in reg.items():
        if prm.typ == "bool" or k in NICHT_VARIIEREN or not p[k]:
            continue
        lo_v, hi_v = prm.clamp(p[k] * (1 - delta)), prm.clamp(p[k] * (1 + delta))
        if lo_v == p[k] and hi_v == p[k]:
            continue
        lo = zielwert(neu_rechnen(R, {**p, k: lo_v}), ziel) - basis
        hi = zielwert(neu_rechnen(R, {**p, k: hi_v}), ziel) - basis
        if abs(lo) < 0.5 and abs(hi) < 0.5:
            continue
        rows.append({"key": k, "Parameter": prm.label, "Einheit": prm.einheit, "Gruppe": prm.gruppe,
                     "Wert": p[k], "niedrig": lo_v, "hoch": hi_v, "Δ niedrig": lo, "Δ hoch": hi,
                     "Spanne": abs(hi - lo)})
    return basis, sorted(rows, key=lambda x: -x["Spanne"])


def sweep(R, reg, key, werte):
    """Kosten aller Verfahren über einen Wertebereich eines Parameters (oder der Wiesenfläche in ha)."""
    out = []
    for v in werte:
        if key == FLAECHE:
            r = neu_rechnen(R, R["p"], wiese={**R["wiese"], "flaeche_m2": v * 10_000})
        else:
            r = neu_rechnen(R, {**R["p"], key: reg[key].clamp(v)})
        out.append({"x": v, **kosten(r)})
    return out


def schnittpunkte(rows, a, b):
    """x-Werte, an denen Verfahren a und b gleich teuer sind (lineare Interpolation zwischen Stützstellen)."""
    xs = []
    for r0, r1 in zip(rows, rows[1:]):
        d0, d1 = r0[a] - r0[b], r1[a] - r1[b]
        if d0 == 0:
            xs.append((r0["x"], "gleich"))
        elif d0 * d1 < 0:
            x = r0["x"] + (r1["x"] - r0["x"]) * d0 / (d0 - d1)
            xs.append((x, f"{a} günstiger" if d1 < 0 else f"{b} günstiger"))
    return xs


def szenarien(R, reg, liste):
    """Jedes Szenario ab Basiswerten neu rechnen, dazu der aktuelle Stand."""
    out = []
    for s in liste:
        r = neu_rechnen(R, registry.scenario_values(reg, s))
        m, k = guenstigstes(r)
        out.append({"Szenario": s["name"], **k, "Günstigstes": m,
                    "Zeit Drohne h": r["drohne"]["Zeit (min)"] / 60, "CO₂ Drohne kg": r["drohne"]["CO₂ (kg)"]})
    m, k = guenstigstes(R)
    out.append({"Szenario": "Aktueller Stand", **k, "Günstigstes": m,
                "Zeit Drohne h": R["drohne"]["Zeit (min)"] / 60, "CO₂ Drohne kg": R["drohne"]["CO₂ (kg)"]})
    return out
