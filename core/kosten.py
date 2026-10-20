"""Zeit, Kosten und CO₂ der drei Transportverfahren.

Alle Verfahren rechnen mit Einsatztagen bzw. Transporten, damit Forst und Heuernte dieselben Bausteine nutzen.

Drohne:      je Einsatztag Anreise + Aufbau/Abbau + Flugbetrieb + ggf. Wartezeit + Drohnenbetrieb + Sonstiges
             Tagestyp "geraete": Geräte morgens hoch, abends runter. Die Drohne wartet dazwischen oder fährt
                                 ein zweites Mal an, die günstigere Variante zählt.
             Tagestyp "dauer":   Drohne ist die ganze Zeit im Einsatz (z. B. Erntetag), Leerlauf wird bezahlt.
             Tagestyp "einfach": nur Hintransport, eine Anfahrt.
Helikopter:  je Einsatz (Anflug von der Basis + Rotationen) × €/min, mindestens Mindestabrechnung,
             + Bereitstellung; optional Zusatzposten (z. B. Geräte, die das Team trägt)
Tragen:      je Transport Gänge × Gehzeit (DIN 33466, Lastaufschlag) × Team × Stundensatz
"""
import math

from .fmt import de
from .trace import Trace


def eff(anbieter, spalte, p, key):
    """Anbieterwert, falls in der Anbieterliste gesetzt, sonst Standardwert aus den Parametern."""
    v = (anbieter or {}).get(spalte)
    return (v, "Anbieter") if v is not None else (p[key], "Standard")


def umlauf(prof, p, tr=None):
    t = prof["out_min"] + prof["back_min"] + p["flug.handling_min"]
    if tr is not None:
        tr.add("Zeit je Umlauf", "t_hin + t_rück + t_Handling",
               f"{de(prof['out_min'], 1)} + {de(prof['back_min'], 1)} + {de(p['flug.handling_min'], 1)} min",
               t, "min", 1, kommentar="Gleich für beladen bergauf (Geräte) und beladen bergab (Heu)")
    return t


# ---------------------------------------------------------------------------
# Drohne
# ---------------------------------------------------------------------------
def drohne(prof, p, an, einsatztage):
    """einsatztage: [{name, anzahl, fluege, modus, warte_h?, praesenz_h?}]
    an: {"anbieter": dict, "km": einfache Strecke, "route_min": Fahrzeit einfach ohne Zuschlag, "quelle": str}"""
    dl = bool(p["modell.dienstleister"])
    auto = bool(p["modell.autonom"]) and not dl
    titel = "Drohne · " + ("Dienstleister" if dl else "Eigenbetrieb" + (" autonom" if auto else ""))
    tr = Trace("drohne", titel,
               "Kosten je Einsatztag aus Anreise, Aufbau und Abbau, Flugbetrieb, ggf. Wartezeit, Drohnenbetrieb "
               "und Sonstigem, anschließend über alle Einsatztage summiert.")
    t_um = umlauf(prof, p, tr)
    n_ges = sum(t["fluege"] * t["anzahl"] for t in einsatztage)
    leer = {"Zeit (min)": 0, "Kosten (€)": 0, "CO₂ (kg)": 0, "umlauf_min": t_um, "fluege": 0, "positionen": [],
            "variante": "", "anfahrten": 0, "tage": 0, "fix": 0, "variabel": 0, "trace": tr}
    if n_ges == 0:
        tr.add("Kosten", "keine Flüge", "", 0, "€", 0)
        return leer

    A, km = an["anbieter"], an["km"]
    zuschlag = p["anreise.zuschlag_min"]
    fahrt_h = tr.add("Fahrzeit je Richtung", "Routing + Zuschlag letzte Meile",
                     f"{de(an['route_min'])} + {de(zuschlag)} min ({an['quelle']})",
                     (an["route_min"] + zuschlag) / 60, "h", 2)
    if auto:
        personen = int(p["autonom.bodenpersonal_n"])
        crew = tr.add("Personalsatz Crew", "Bodenpersonal × Satz Helfer (kein Pilot)",
                      f"{personen} × {de(p['personal.helfer_eur_h'])} €/h", personen * p["personal.helfer_eur_h"],
                      "€/h", 0)
    else:
        personen = 1 + int(p["personal.helfer_n"])
        crew = tr.add("Personalsatz Crew", "Pilot + Helfer × Satz Helfer",
                      f"{de(p['personal.pilot_eur_h'])} + {int(p['personal.helfer_n'])} × "
                      f"{de(p['personal.helfer_eur_h'])} €/h",
                      p["personal.pilot_eur_h"] + p["personal.helfer_n"] * p["personal.helfer_eur_h"], "€/h", 0)

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
        satz, q4 = eff(A, "einsatz_eur_h", p, "dl.einsatz_eur_h")
    else:
        pers = tr.add("Anreise Personal je Anfahrt", "2 × Fahrzeit × Personalsatz Crew",
                      f"2 × {de(fahrt_h, 2)} h × {de(crew)} €/h", 2 * fahrt_h * crew, "€", 0)
        satz, q4 = crew, "Crew"
    ruest_h = (p["einsatz.aufbau_min"] + p["einsatz.abbau_min"]) / 60
    if dl and not p["dl.aufbau_abgerechnet"]:
        ruest = tr.add("Aufbau und Abbau je Anfahrt", "im Angebot nicht abgerechnet", "", 0, "€", 0)
    else:
        ruest = tr.add("Aufbau und Abbau je Anfahrt", "(Aufbau + Abbau) × Stundensatz",
                       f"{de(ruest_h, 2)} h × {de(satz)} €/h ({q4})", ruest_h * satz, "€", 0)
    besuch = fz + pers + ruest
    mit_betrieb = (not dl) or (not p["dl.betrieb_inkl"])
    if not mit_betrieb:
        tr.add("Drohnenbetrieb", "im Stundensatz des Dienstleisters enthalten", "", 0, "€", 0)

    pos, varianten, zeit, co2, anfahrten_ges, tage_ges = [], [], 0.0, 0.0, 0, 0
    for t in einsatztage:
        n, k, name = t["fluege"], t["anzahl"], t["name"]
        if n == 0 or k == 0:
            continue
        flug_min = n * t_um
        flug_h = flug_min / 60
        tr.add(f"{name}: Flugzeit", "Flüge × Zeit je Umlauf", f"{n} × {de(t_um, 1)} min", flug_min, "min", 0,
               kommentar=f"{k} Tag(e) dieses Typs")
        if dl:
            flug = tr.add(f"{name}: Flugbetrieb", "Flugzeit × Einsatzstundensatz + Flüge × Zuschlag je Flug",
                          f"{de(flug_h, 2)} h × {de(satz)} €/h + {n} × {de(p['dl.flug_eur'])} €",
                          flug_h * satz + n * p["dl.flug_eur"], "€", 0, kommentar="Pilot im Stundensatz enthalten")
        else:
            flug = tr.add(f"{name}: Flugbetrieb Personal", "Flugzeit × Personalsatz Crew",
                          f"{de(flug_h, 2)} h × {de(crew)} €/h", flug_h * crew, "€", 0)
            if auto:
                flug += tr.add(f"{name}: Fernüberwachung", "Flugzeit × Satz Fernüberwachung",
                               f"{de(flug_h, 2)} h × {de(p['autonom.ueberwachung_eur_h'])} €/h",
                               flug_h * p["autonom.ueberwachung_eur_h"], "€", 0)
        if t["modus"] == "geraete":
            warte_h = t["warte_h"]
            va = tr.add(f"{name}: Variante bleibt vor Ort", "Anreise + Aufbau/Abbau + Wartezeit × Stundensatz",
                        f"{de(besuch)} € + {de(warte_h, 1)} h × {de(satz)} €/h", besuch + warte_h * satz, "€", 0,
                        kommentar="Wartezeit = Arbeitszeit des Teams zwischen Hin- und Rücktransport")
            vb = tr.add(f"{name}: Variante zweite Anfahrt", "2 × (Anreise + Aufbau/Abbau)", f"2 × {de(besuch)} €",
                        2 * besuch, "€", 0)
            anf, warte = (1, warte_h * satz) if va <= vb else (2, 0.0)
            varianten.append(f"{name}: " + ("bleibt vor Ort" if anf == 1 else "zweite Anfahrt"))
            vor_ort_min = anf * ruest_h * 60 + flug_min
        elif t["modus"] == "dauer":
            praesenz = t["praesenz_h"]
            leerlauf = max(0.0, praesenz - flug_h)
            warte = tr.add(f"{name}: Leerlauf", "(Einsatzdauer − Flugzeit) × Stundensatz",
                           f"({de(praesenz, 1)} − {de(flug_h, 1)}) h × {de(satz)} €/h", leerlauf * satz, "€", 0,
                           kommentar="Drohne bleibt den ganzen Tag, wartet auf befüllte Säcke")
            anf = 1
            varianten.append(f"{name}: ganztägig")
            vor_ort_min = ruest_h * 60 + max(praesenz, flug_h) * 60
        else:
            anf, warte = 1, 0.0
            vor_ort_min = ruest_h * 60 + flug_min
        betr_fix = betr_var = 0.0
        if mit_betrieb:
            betr_fix = p["betrieb.abschreibung_eur_tag"] + p["betrieb.versicherung_eur_tag"]
            betr_var = tr.add(f"{name}: Drohnenbetrieb variabel",
                              "Flugzeit × (Wartung + Akkualterung) + Flüge × kWh × Strompreis",
                              f"{de(flug_h, 2)} h × ({de(p['betrieb.wartung_eur_fh'])} + "
                              f"{de(p['betrieb.akku_eur_fh'])}) €/h + {n} × {de(p['drohne.energie_kwh_flug'], 1)} kWh × "
                              f"{de(p['betrieb.strom_eur_kwh'], 2)} €/kWh",
                              flug_h * (p["betrieb.wartung_eur_fh"] + p["betrieb.akku_eur_fh"])
                              + n * p["drohne.energie_kwh_flug"] * p["betrieb.strom_eur_kwh"], "€", 0)
        posten = [("Anreise Fahrzeug", "Anreise", "fix", anf * fz, f"{anf} × {de(fz)} €"),
                  ("Anreise Personal", "Anreise", "fix", anf * pers, f"{anf} × {de(pers)} €"),
                  ("Aufbau und Abbau", "Vor Ort", "fix", anf * ruest, f"{anf} × {de(ruest)} €"),
                  ("Flugbetrieb", "Flugbetrieb", "variabel", flug, f"{n} Flüge"),
                  ("Wartezeit / Leerlauf", "Vor Ort", "fix", warte, "")]
        if mit_betrieb:
            posten += [("Drohnenbetrieb fix", "Drohnenbetrieb", "fix", betr_fix,
                        f"{de(p['betrieb.abschreibung_eur_tag'])} + {de(p['betrieb.versicherung_eur_tag'])} €"),
                       ("Drohnenbetrieb variabel", "Drohnenbetrieb", "variabel", betr_var, "")]
        if p["betrieb.sonstiges_eur"]:
            posten.append(("Sonstiges", "Sonstiges", "fix", p["betrieb.sonstiges_eur"], ""))
        for pname, gruppe, art, betrag, eins in posten:
            if betrag:
                pos.append({"Einsatztag": name, "Position": pname, "Gruppe": gruppe, "Art": art,
                            "Betrag": betrag * k, "Eingesetzt": (f"{k} × ({eins})" if k > 1 else eins)})
        zeit += k * vor_ort_min
        co2 += k * (n * p["drohne.energie_kwh_flug"] * p["co2.strom_kg_kwh"] + anf * 2 * km * p["co2.fahrzeug_kg_km"])
        anfahrten_ges += k * anf
        tage_ges += k

    total = sum(x["Betrag"] for x in pos)
    tr.add("Kosten gesamt", "Σ Positionen aller Einsatztage", f"{tage_ges} Einsatztag(e) · {anfahrten_ges} Anfahrt(en)",
           total, "€", 0)
    tr.add("Zeit vor Ort", "Σ Tage × (Anfahrten × (Aufbau + Abbau) + Flugzeit bzw. Einsatzdauer)", "", zeit, "min", 0,
           kommentar="Ohne Fahrzeit; Wartezeit zwischen Hin- und Rücktransport nicht enthalten")
    tr.add("CO₂", "Σ Flüge × kWh × Strommix + Anfahrten × 2 × km × Faktor Fahrzeug",
           f"{de(p['drohne.energie_kwh_flug'], 1)} kWh · {de(p['co2.strom_kg_kwh'], 2)} kg/kWh · "
           f"{de(p['co2.fahrzeug_kg_km'], 2)} kg/km", co2, "kg", 1)
    return {**leer, "Zeit (min)": zeit, "Kosten (€)": total, "CO₂ (kg)": co2, "fluege": n_ges, "positionen": pos,
            "variante": " · ".join(varianten), "anfahrten": anfahrten_ges, "tage": tage_ges,
            "fix": sum(x["Betrag"] for x in pos if x["Art"] == "fix"),
            "variabel": sum(x["Betrag"] for x in pos if x["Art"] == "variabel")}


# ---------------------------------------------------------------------------
# Helikopter
# ---------------------------------------------------------------------------
def heli(brutto, einsaetze, p, basis, beschreibung="", zusatz=()):
    """brutto je Einsatz, einsaetze = Anzahl Anflüge. zusatz: [(Name, Kosten €, Zeit min)] z. B. Geräte tragen."""
    tr = Trace("heli", "Helikopter",
               "Abrechnung nach Flugminuten. Der Anflug wird aus der Luftlinie zur Basis berechnet. " + beschreibung)
    A, km = basis["anbieter"], basis["km"]
    out = {"Zeit (min)": 0, "Kosten (€)": 0, "CO₂ (kg)": 0, "rotationen": 0, "einsaetze": 0, "anflug_min": 0,
           "trace": tr}
    if brutto <= 0 or einsaetze <= 0:
        tr.add("Kosten", "keine Fracht", "", 0, "€", 0)
        return out
    tr.add("Einsätze", "Anzahl Anflüge", beschreibung[:80], einsaetze, "", 0)
    anflug = tr.add("Anflug je Einsatz", "2 × Luftlinie Basis ↔ Landeplatz / Transfergeschwindigkeit",
                    f"2 × {de(km, 1)} km / {de(p['heli.v_kmh'])} km/h ({A['name']})",
                    2 * km / p["heli.v_kmh"] * 60, "min", 1)
    rot = tr.add("Rotationen je Einsatz", "⌈Bruttogewicht je Einsatz / Nutzlast je Rotation⌉",
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
    kosten = einsaetze * je
    zeit = einsaetze * rot * p["heli.rotation_min"]
    for name, k, z in zusatz:
        tr.add(name, "aus manuellem Transport", "Team trägt, Heli fliegt nur die Hauptlast", k, "€", 0,
               kommentar=f"{de(z / 60, 1)} h")
        kosten += k
        zeit += z
    tr.add("Kosten gesamt", "Einsätze × Kosten je Einsatz + Zusatzposten", f"{einsaetze} × {de(je)} €", kosten, "€", 0)
    tr.add("Zeit vor Ort", "Einsätze × Rotationen × Dauer je Rotation + Zusatzposten", "", zeit, "min", 0,
           kommentar="Anflug ist in den Kosten enthalten, aber keine Zeit am Hang")
    co2 = tr.add("CO₂", "Einsätze × Flugstunden × Verbrauch × Emissionsfaktor",
                 f"{einsaetze} × {de(minuten / 60, 2)} h × {de(p['heli.kerosin_l_h'])} l/h × "
                 f"{de(p['co2.kerosin_kg_l'], 2)} kg/l", einsaetze * minuten / 60 * p["heli.kerosin_l_h"]
                 * p["co2.kerosin_kg_l"], "kg", 1)
    return {**out, "Zeit (min)": zeit, "Kosten (€)": kosten, "CO₂ (kg)": co2, "rotationen": rot,
            "einsaetze": einsaetze, "anflug_min": anflug}


# ---------------------------------------------------------------------------
# Tragen
# ---------------------------------------------------------------------------
def _din33466(km, auf, ab, p):
    """Gehzeit nach DIN 33466: max(t_horizontal, t_vertikal) + min(t_horizontal, t_vertikal) / 2."""
    th = km / p["manuell.v_horizontal_kmh"]
    tv = auf / p["manuell.aufstieg_hm_h"] + ab / p["manuell.abstieg_hm_h"]
    return max(th, tv) + min(th, tv) / 2, th, tv


def manuell(prof, p, team, laeufe, titel="Manueller Transport", trace=True):
    """laeufe: [{name, kg, traglast, richtung: "hoch" | "runter", anzahl}]
    Jeder Gang: Weg mit Last (× Lastfaktor) in Transportrichtung, leer zurück."""
    tr = Trace("manuell", titel,
               "Das Team trägt die Fracht ohne Boxen. Gehzeit nach DIN 33466 (Wanderzeitberechnung) mit "
               "Zeitaufschlag für den Weg mit Last. Strecke und Höhenmeter aus dem Geländeprofil.")
    km, auf, ab = prof["dist"] / 1000, prof["asc"], prof["desc"]
    t_hoch, th, tv_h = _din33466(km, auf, ab, p)
    t_runter, _, tv_r = _din33466(km, ab, auf, p)
    tr.add("Gehzeit bergauf", "max(t_h, t_v) + min(t_h, t_v) / 2 · t_h = km / v · t_v = ↑/v_auf + ↓/v_ab",
           f"t_h = {de(km, 2)} km / {de(p['manuell.v_horizontal_kmh'], 1)} km/h = {de(th, 2)} h · "
           f"t_v = {de(auf)}/{de(p['manuell.aufstieg_hm_h'])} + {de(ab)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv_h, 2)} h",
           t_hoch, "h", 2, kommentar="Landeplatz → Einsatzort, ohne Lastaufschlag")
    tr.add("Gehzeit bergab", "wie bergauf, Höhenmeter vertauscht",
           f"t_v = {de(ab)}/{de(p['manuell.aufstieg_hm_h'])} + {de(auf)}/{de(p['manuell.abstieg_hm_h'])} = {de(tv_r, 2)} h",
           t_runter, "h", 2)
    lf = p["manuell.lastfaktor"]
    stunden, gaenge_ges = 0.0, 0
    for lauf in laeufe:
        if lauf["kg"] <= 0 or lauf["anzahl"] <= 0:
            continue
        g = math.ceil(lauf["kg"] / (team * lauf["traglast"]))
        gang = (t_hoch * lf + t_runter) if lauf["richtung"] == "hoch" else (t_runter * lf + t_hoch)
        h = tr.add(lauf["name"], "Anzahl × ⌈kg / (Team × Traglast)⌉ × (Weg mit Last × Lastfaktor + Weg leer)",
                   f"{lauf['anzahl']} × ⌈{de(lauf['kg'], 1)} / ({team} × {de(lauf['traglast'])})⌉ = "
                   f"{lauf['anzahl'] * g} Gänge × {de(gang, 2)} h", lauf["anzahl"] * g * gang, "h", 1)
        stunden += h
        gaenge_ges += lauf["anzahl"] * g
    kosten = tr.add("Kosten", "Zeit × Team × Stundensatz",
                    f"{de(stunden, 2)} h × {team} × {de(p['manuell.stundensatz_eur_h'])} €/h",
                    stunden * team * p["manuell.stundensatz_eur_h"], "€", 0,
                    kommentar="Alle Personen gehen gleichzeitig")
    return {"Zeit (min)": stunden * 60, "Kosten (€)": kosten, "CO₂ (kg)": 0.0, "gaenge": gaenge_ges, "trace": tr}
