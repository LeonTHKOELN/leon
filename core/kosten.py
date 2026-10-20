"""Zeit, Kosten und CO₂ der drei Transportverfahren.

Drohne:      Anreise + Aufbau/Abbau + Flugbetrieb (Personal) + ggf. Wartezeit + Drohnenbetrieb + Sonstiges
Helikopter:  (Anflug von der Basis + Rotationen) × €/min, mindestens Mindestabrechnung, + Bereitstellung
Tragen:      Gänge × Gehzeit (DIN 33466, mit Lastaufschlag) × Team × Stundensatz

Rücktransport am Einsatzende verdoppelt die Transporte. Die Drohne kann dafür vor Ort warten
oder ein zweites Mal anfahren. Die App rechnet beides und nimmt die günstigere Variante.
"""
import math

from .fmt import de
from .trace import Trace


def eff(anbieter, spalte, p, key):
    """Anbieterwert, falls in der Anbieterliste gesetzt, sonst Standardwert aus den Parametern."""
    v = (anbieter or {}).get(spalte)
    return (v, "Anbieter") if v is not None else (p[key], "Standard")


def _pos(liste, name, gruppe, art, betrag, formel, einsetzung):
    liste.append({"Position": name, "Gruppe": gruppe, "Art": art, "Betrag": betrag,
                  "Formel": formel, "Eingesetzt": einsetzung})
    return betrag


# ---------------------------------------------------------------------------
# Drohne
# ---------------------------------------------------------------------------
def drohne(prof, pk, p, job, an):
    """an: {"anbieter": dict, "km": einfache Strecke, "route_min": Fahrzeit einfach ohne Zuschlag, "quelle": str}"""
    dl = bool(p["modell.dienstleister"])
    auto = bool(p["modell.autonom"]) and not dl
    tage, rueck = max(1, job["tage"]), bool(job["rueck"])
    titel = "Drohne · " + ("Dienstleister" if dl else "Eigenbetrieb" + (" autonom" if auto else ""))
    tr = Trace("drohne", titel,
               "Kosten je Einsatztag aus Anreise, Aufbau und Abbau, Flugbetrieb, ggf. Wartezeit, Drohnenbetrieb "
               "und Sonstigem. Bei Rücktransport werden die Varianten 'bleibt vor Ort' und 'zweite Anfahrt' "
               "verglichen.")

    n = len(pk["flights"])
    blocks = 2 if rueck else 1
    umlauf = tr.add("Zeit je Umlauf", "t_hin + t_rück + t_Handling",
                    f"{de(prof['out_min'], 1)} + {de(prof['back_min'], 1)} + {de(p['flug.handling_min'], 1)} min",
                    prof["out_min"] + prof["back_min"] + p["flug.handling_min"], "min", 1)
    flug_min = tr.add("Flugzeit je Einsatztag", "Flüge × Transporte × Zeit je Umlauf",
                      f"{n} × {blocks} × {de(umlauf, 1)} min", n * blocks * umlauf, "min", 0,
                      kommentar="Transporte = 2 bei Rücktransport am Einsatzende")
    flug_h = flug_min / 60
    if n == 0:
        tr.add("Kosten", "keine Flüge", "", 0, "€", 0)
        return {"Zeit (min)": 0, "Kosten (€)": 0, "CO₂ (kg)": 0, "umlauf_min": umlauf, "fluege": 0,
                "positionen": [], "variante": "", "anfahrten": 0, "trace": tr, "tage": tage,
                "fix": 0, "variabel": 0}

    A = an["anbieter"]
    km = an["km"]
    zuschlag = p["anreise.zuschlag_min"]
    fahrt_h = tr.add("Fahrzeit je Richtung", "Routing + Zuschlag letzte Meile",
                     f"{de(an['route_min'])} + {de(zuschlag)} min ({an['quelle']})",
                     (an["route_min"] + zuschlag) / 60, "h", 2)

    # Personal
    if auto:
        personen = int(p["autonom.bodenpersonal_n"])
        crew_satz = tr.add("Personalsatz Crew", "Bodenpersonal × Satz Helfer (kein Pilot)",
                           f"{personen} × {de(p['personal.helfer_eur_h'])} €/h",
                           personen * p["personal.helfer_eur_h"], "€/h", 0)
    else:
        personen = 1 + int(p["personal.helfer_n"])
        crew_satz = tr.add("Personalsatz Crew", "Pilot + Helfer × Satz Helfer",
                           f"{de(p['personal.pilot_eur_h'])} + {int(p['personal.helfer_n'])} × "
                           f"{de(p['personal.helfer_eur_h'])} €/h",
                           p["personal.pilot_eur_h"] + p["personal.helfer_n"] * p["personal.helfer_eur_h"], "€/h", 0)

    # Anreise (je Anfahrt)
    pauschale, q1 = eff(A, "pauschale_eur", p, "anreise.pauschale_eur")
    eur_km, q2 = eff(A, "eur_km", p, "anreise.eur_km")
    fz = tr.add("Anreise Fahrzeug je Anfahrt", "Pauschale + 2 × km × €/km",
                f"{de(pauschale)} € ({q1}) + 2 × {de(km, 1)} km × {de(eur_km, 2)} €/km ({q2})",
                pauschale + 2 * km * eur_km, "€", 0)
    if dl:
        fahrt_satz, q3 = eff(A, "fahrt_eur_h", p, "dl.fahrt_eur_h")
        pers = tr.add("Anreise Personal je Anfahrt", "2 × Fahrzeit × Satz Fahrzeit × Personen",
                      f"2 × {de(fahrt_h, 2)} h × {de(fahrt_satz)} €/h ({q3}) × {personen}",
                      2 * fahrt_h * fahrt_satz * personen, "€", 0)
    else:
        pers = tr.add("Anreise Personal je Anfahrt", "2 × Fahrzeit × Personalsatz Crew",
                      f"2 × {de(fahrt_h, 2)} h × {de(crew_satz)} €/h", 2 * fahrt_h * crew_satz, "€", 0)

    # Aufbau und Abbau (je Anfahrt)
    ruest_h = (p["einsatz.aufbau_min"] + p["einsatz.abbau_min"]) / 60
    if dl:
        satz, q4 = eff(A, "einsatz_eur_h", p, "dl.einsatz_eur_h")
        ruest = tr.add("Aufbau und Abbau je Anfahrt",
                       "(Aufbau + Abbau) × Einsatzstundensatz" if p["dl.aufbau_abgerechnet"] else "nicht abgerechnet",
                       f"{de(ruest_h, 2)} h × {de(satz)} €/h ({q4})",
                       ruest_h * satz if p["dl.aufbau_abgerechnet"] else 0, "€", 0)
    else:
        ruest = tr.add("Aufbau und Abbau je Anfahrt", "(Aufbau + Abbau) × Personalsatz Crew",
                       f"{de(ruest_h, 2)} h × {de(crew_satz)} €/h", ruest_h * crew_satz, "€", 0)

    # Flugbetrieb (je Einsatztag)
    if dl:
        flug_pers = tr.add("Flugbetrieb", "Flugzeit × Einsatzstundensatz + Flüge × Zuschlag je Flug",
                           f"{de(flug_h, 2)} h × {de(satz)} €/h + {n * blocks} × {de(p['dl.flug_eur'])} €",
                           flug_h * satz + n * blocks * p["dl.flug_eur"], "€", 0,
                           kommentar="Pilot ist im Stundensatz enthalten")
        warte_satz = satz
    else:
        flug_pers = tr.add("Flugbetrieb Personal", "Flugzeit × Personalsatz Crew",
                           f"{de(flug_h, 2)} h × {de(crew_satz)} €/h", flug_h * crew_satz, "€", 0)
        if auto:
            flug_pers += tr.add("Fernüberwachung", "Flugzeit × Satz Fernüberwachung",
                                f"{de(flug_h, 2)} h × {de(p['autonom.ueberwachung_eur_h'])} €/h",
                                flug_h * p["autonom.ueberwachung_eur_h"], "€", 0)
        warte_satz = crew_satz

    # Drohnenbetrieb
    mit_betrieb = (not dl) or (not p["dl.betrieb_inkl"])
    if mit_betrieb:
        betr_fix = tr.add("Drohnenbetrieb fix je Tag", "Abschreibung/Miete + Versicherung",
                          f"{de(p['betrieb.abschreibung_eur_tag'])} + {de(p['betrieb.versicherung_eur_tag'])} €",
                          p["betrieb.abschreibung_eur_tag"] + p["betrieb.versicherung_eur_tag"], "€", 0)
        betr_var = tr.add("Drohnenbetrieb variabel je Tag",
                          "Flugzeit × (Wartung + Akkualterung) + Flüge × kWh × Strompreis",
                          f"{de(flug_h, 2)} h × ({de(p['betrieb.wartung_eur_fh'])} + {de(p['betrieb.akku_eur_fh'])}) €/h"
                          f" + {n * blocks} × {de(p['drohne.energie_kwh_flug'], 1)} kWh × "
                          f"{de(p['betrieb.strom_eur_kwh'], 2)} €/kWh",
                          flug_h * (p["betrieb.wartung_eur_fh"] + p["betrieb.akku_eur_fh"])
                          + n * blocks * p["drohne.energie_kwh_flug"] * p["betrieb.strom_eur_kwh"], "€", 0)
    else:
        betr_fix = betr_var = 0
        tr.add("Drohnenbetrieb", "im Stundensatz des Dienstleisters enthalten", "", 0, "€", 0)
    sonst = p["betrieb.sonstiges_eur"]

    # Varianten
    besuch = fz + pers + ruest
    if rueck:
        warte_h = job["dauer_h"]
        var_a = tr.add("Variante A: bleibt vor Ort", "1 × (Anreise + Aufbau/Abbau) + Wartezeit × Satz",
                       f"{de(besuch)} € + {de(warte_h)} h × {de(warte_satz)} €/h",
                       besuch + warte_h * warte_satz, "€", 0,
                       kommentar="Wartezeit = Arbeitszeit des Teams am Hang")
        var_b = tr.add("Variante B: zweite Anfahrt", "2 × (Anreise + Aufbau/Abbau)", f"2 × {de(besuch)} €",
                       2 * besuch, "€", 0)
        variante = "bleibt vor Ort" if var_a <= var_b else "zweite Anfahrt"
        tr.add("Gewählt", "günstigere Variante", f"A {de(var_a)} € · B {de(var_b)} €", 0, text=variante)
        anfahrten = 1 if var_a <= var_b else 2
        warte = warte_h * warte_satz if anfahrten == 1 else 0
    else:
        variante, anfahrten, warte = "ohne Rücktransport", 1, 0

    pos = []
    _pos(pos, "Anreise Fahrzeug", "Anreise", "fix", anfahrten * fz * tage, "Anfahrten × Tage × je Anfahrt",
         f"{anfahrten} × {tage} × {de(fz)} €")
    _pos(pos, "Anreise Personal", "Anreise", "fix", anfahrten * pers * tage, "Anfahrten × Tage × je Anfahrt",
         f"{anfahrten} × {tage} × {de(pers)} €")
    _pos(pos, "Aufbau und Abbau", "Vor Ort", "fix", anfahrten * ruest * tage, "Anfahrten × Tage × je Anfahrt",
         f"{anfahrten} × {tage} × {de(ruest)} €")
    _pos(pos, "Flugbetrieb" if dl else "Flugbetrieb Personal", "Flugbetrieb", "variabel", flug_pers * tage,
         "Tage × je Tag", f"{tage} × {de(flug_pers)} €")
    if warte:
        _pos(pos, "Wartezeit vor Ort", "Vor Ort", "fix", warte * tage, "Tage × je Tag", f"{tage} × {de(warte)} €")
    if mit_betrieb:
        _pos(pos, "Drohnenbetrieb fix", "Drohnenbetrieb", "fix", betr_fix * tage, "Tage × je Tag",
             f"{tage} × {de(betr_fix)} €")
        _pos(pos, "Drohnenbetrieb variabel", "Drohnenbetrieb", "variabel", betr_var * tage, "Tage × je Tag",
             f"{tage} × {de(betr_var)} €")
    if sonst:
        _pos(pos, "Sonstiges", "Sonstiges", "fix", sonst * tage, "Tage × je Tag", f"{tage} × {de(sonst)} €")
    total = sum(x["Betrag"] for x in pos)
    tr.add("Kosten gesamt", "Σ Positionen", f"{tage} Einsatztag(e) · {variante}", total, "€", 0)
    zeit = tr.add("Zeit vor Ort", "Tage × (Anfahrten × (Aufbau + Abbau) + Flugzeit je Tag)",
                  f"{tage} × ({anfahrten} × {de(ruest_h * 60)} + {de(flug_min)}) min",
                  tage * (anfahrten * ruest_h * 60 + flug_min), "min", 0,
                  kommentar="Ohne Fahrzeit und ohne Wartezeit; vergleichbar mit der Zeit am Hang der anderen Verfahren")
    co2_flug = n * blocks * tage * p["drohne.energie_kwh_flug"] * p["co2.strom_kg_kwh"]
    co2_fz = anfahrten * tage * 2 * km * p["co2.fahrzeug_kg_km"]
    co2 = tr.add("CO₂", "Flugbetrieb (Flüge × Transporte × Tage × kWh × Strommix) + Anfahrt (Anfahrten × Tage × 2 × km × Faktor)",
                 f"{n} × {blocks} × {tage} × {de(p['drohne.energie_kwh_flug'], 1)} kWh × "
                 f"{de(p['co2.strom_kg_kwh'], 2)} kg/kWh + {anfahrten} × {tage} × 2 × {de(km, 1)} km × "
                 f"{de(p['co2.fahrzeug_kg_km'], 2)} kg/km", co2_flug + co2_fz, "kg", 1)
    return {"Zeit (min)": zeit, "Kosten (€)": total, "CO₂ (kg)": co2, "umlauf_min": umlauf,
            "fluege": n, "positionen": pos, "variante": variante, "anfahrten": anfahrten, "tage": tage,
            "fix": sum(x["Betrag"] for x in pos if x["Art"] == "fix"),
            "variabel": sum(x["Betrag"] for x in pos if x["Art"] == "variabel"), "trace": tr}


# ---------------------------------------------------------------------------
# Helikopter
# ---------------------------------------------------------------------------
def heli(pk, p, job, basis):
    """basis: {"anbieter": dict, "km": Luftlinie Basis → Landeplatz}"""
    tr = Trace("heli", "Helikopter",
               "Abrechnung nach Flugminuten. Der Anflug wird aus der Luftlinie zur Basis berechnet. "
               "Jeder Einsatz (Hin- und ggf. Rücktransport, je Tag) ist ein eigener Anflug.")
    A, km = basis["anbieter"], basis["km"]
    brutto = pk["brutto"]
    tage, rueck = max(1, job["tage"]), bool(job["rueck"])
    if brutto <= 0:
        tr.add("Kosten", "keine Fracht", "", 0, "€", 0)
        return {"Zeit (min)": 0, "Kosten (€)": 0, "CO₂ (kg)": 0, "rotationen": 0, "einsaetze": 0,
                "anflug_min": 0, "trace": tr}
    einsaetze = tr.add("Einsätze", "Tage × Transporte", f"{tage} × {2 if rueck else 1}",
                       tage * (2 if rueck else 1), "", 0)
    anflug = tr.add("Anflug je Einsatz", "2 × Luftlinie Basis ↔ Landeplatz / Transfergeschwindigkeit",
                    f"2 × {de(km, 1)} km / {de(p['heli.v_kmh'])} km/h ({A['name']})",
                    2 * km / p["heli.v_kmh"] * 60, "min", 1)
    rot = tr.add("Rotationen je Einsatz", "⌈Bruttogewicht / Nutzlast je Rotation⌉",
                 f"⌈{de(brutto, 1)} kg / {de(p['heli.nutzlast_kg'])} kg⌉",
                 math.ceil(brutto / p["heli.nutzlast_kg"]), "", 0)
    minuten = tr.add("Flugminuten je Einsatz", "Anflug + Rotationen × Dauer je Rotation",
                     f"{de(anflug, 1)} + {rot} × {de(p['heli.rotation_min'])} min",
                     anflug + rot * p["heli.rotation_min"], "min", 1)
    mindest, q1 = eff(A, "heli_mindest_min", p, "heli.mindest_min")
    abgerechnet = tr.add("Abgerechnete Minuten je Einsatz", "max(Flugminuten, Mindestabrechnung)",
                         f"max({de(minuten, 1)}, {de(mindest)}) min ({q1})", max(minuten, mindest), "min", 1)
    eur_min, q2 = eff(A, "heli_eur_min", p, "heli.eur_min")
    bereit, q3 = eff(A, "heli_bereitstellung_eur", p, "heli.bereitstellung_eur")
    je = tr.add("Kosten je Einsatz", "abgerechnete Minuten × €/min + Bereitstellung",
                f"{de(abgerechnet, 1)} min × {de(eur_min)} €/min ({q2}) + {de(bereit)} € ({q3})",
                abgerechnet * eur_min + bereit, "€", 0)
    kosten = tr.add("Kosten gesamt", "Einsätze × Kosten je Einsatz", f"{einsaetze} × {de(je)} €",
                    einsaetze * je, "€", 0)
    co2 = tr.add("CO₂", "Einsätze × Flugstunden × Verbrauch × Emissionsfaktor",
                 f"{einsaetze} × {de(minuten / 60, 2)} h × {de(p['heli.kerosin_l_h'])} l/h × "
                 f"{de(p['co2.kerosin_kg_l'], 2)} kg/l",
                 einsaetze * minuten / 60 * p["heli.kerosin_l_h"] * p["co2.kerosin_kg_l"], "kg", 1)
    zeit = tr.add("Zeit vor Ort", "Einsätze × Rotationen × Dauer je Rotation",
                  f"{einsaetze} × {rot} × {de(p['heli.rotation_min'])} min", einsaetze * rot * p["heli.rotation_min"],
                  "min", 0, kommentar="Anflug von der Basis ist in den Kosten enthalten, aber keine Zeit am Hang")
    return {"Zeit (min)": zeit, "Kosten (€)": kosten, "CO₂ (kg)": co2, "rotationen": rot,
            "einsaetze": einsaetze, "anflug_min": anflug, "trace": tr}


# ---------------------------------------------------------------------------
# Tragen
# ---------------------------------------------------------------------------
def _din33466(km, auf, ab, p):
    """Gehzeit nach DIN 33466: max(t_horizontal, t_vertikal) + min(t_horizontal, t_vertikal) / 2."""
    th = km / p["manuell.v_horizontal_kmh"]
    tv = auf / p["manuell.aufstieg_hm_h"] + ab / p["manuell.abstieg_hm_h"]
    return max(th, tv) + min(th, tv) / 2, th, tv


def manuell(prof, pk, job, p):
    tr = Trace("manuell", "Manueller Transport",
               "Das Team trägt die Fracht ohne Boxen. Gehzeit nach DIN 33466 (Wanderzeitberechnung) mit "
               "Zeitaufschlag für den Weg mit Last. Strecke und Höhenmeter aus dem Geländeprofil.")
    team, netto = job["team"], pk["netto"]
    tage, rueck = max(1, job["tage"]), bool(job["rueck"])
    gaenge = tr.add("Gänge je Transport", "⌈Nettogewicht / (Team × Traglast)⌉",
                    f"⌈{de(netto, 1)} kg / ({team} × {de(p['manuell.traglast_kg'])} kg)⌉",
                    math.ceil(netto / (team * p["manuell.traglast_kg"])) if netto else 0, "", 0)
    transporte = tage * (2 if rueck else 1)
    km = prof["dist"] / 1000
    auf, ab = prof["asc"], prof["desc"]
    t_last, th, tv = _din33466(km, auf, ab, p)
    t_leer, _, tv2 = _din33466(km, ab, auf, p)
    tr.add("Gehzeit Hinweg (mit Last)", "max(t_h, t_v) + min(t_h, t_v) / 2 · t_h = km / v · t_v = ↑/v_auf + ↓/v_ab",
           f"t_h = {de(km, 2)} km / {de(p['manuell.v_horizontal_kmh'], 1)} km/h = {de(th, 2)} h · "
           f"t_v = {de(auf)}/{de(p['manuell.aufstieg_hm_h'])} + {de(ab)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv, 2)} h",
           t_last, "h", 2, kommentar="Landeplatz → Einsatzort, Zeit ohne Lastaufschlag")
    tr.add("Gehzeit Rückweg (ohne Last)", "wie Hinweg, Höhenmeter vertauscht",
           f"t_v = {de(ab)}/{de(p['manuell.aufstieg_hm_h'])} + {de(auf)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv2, 2)} h",
           t_leer, "h", 2)
    gang_h = tr.add("Zeit je Gang", "Weg mit Last × Lastfaktor + Weg ohne Last",
                    f"{de(t_last, 2)} h × {de(p['manuell.lastfaktor'], 2)} + {de(t_leer, 2)} h",
                    t_last * p["manuell.lastfaktor"] + t_leer, "h", 2,
                    kommentar="Bergauf getragen; beim Rücktransport ist die Last bergab, gleicher Ansatz")
    zeit_h = tr.add("Zeit gesamt", "Transporte × Gänge × Zeit je Gang",
                    f"{transporte} × {gaenge} × {de(gang_h, 2)} h", transporte * gaenge * gang_h, "h", 1,
                    kommentar="Transporte = Tage × (2 bei Rücktransport); alle Personen gehen gleichzeitig")
    kosten = tr.add("Kosten", "Zeit × Team × Stundensatz",
                    f"{de(zeit_h, 2)} h × {team} × {de(p['manuell.stundensatz_eur_h'])} €/h",
                    zeit_h * team * p["manuell.stundensatz_eur_h"], "€", 0)
    return {"Zeit (min)": zeit_h * 60, "Kosten (€)": kosten, "CO₂ (kg)": 0.0, "gaenge": gaenge * transporte,
            "trace": tr}
