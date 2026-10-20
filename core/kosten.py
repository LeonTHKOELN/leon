"""Zeit, Kosten und CO₂ der drei Transportverfahren."""
import math

from .fmt import de
from .trace import Trace


def drohne(prof, pk, p):
    tr = Trace("drohne", "Drohne",
               "Vereinfachtes Dienstleistermodell: Pauschale plus Preis je Flug. "
               "Phase 2 ersetzt dies durch Anreise, Aufbau, Pilot, Betrieb und Abbau.")
    n = len(pk["flights"])
    umlauf = tr.add("Zeit je Umlauf", "t_hin + t_rück + t_Handling",
                    f"{de(prof['out_min'], 1)} + {de(prof['back_min'], 1)} + {de(p['flug.handling_min'], 1)} min",
                    prof["out_min"] + prof["back_min"] + p["flug.handling_min"], "min", 1)
    zeit = tr.add("Zeit gesamt", "Flüge × Zeit je Umlauf", f"{n} × {de(umlauf, 1)} min", n * umlauf, "min", 0)
    kosten = tr.add("Kosten", "Pauschale + Flüge × Kosten je Flug",
                    f"{de(p['drohne.pauschale_eur'])} € + {n} × {de(p['drohne.kosten_flug_eur'])} €",
                    (p["drohne.pauschale_eur"] + n * p["drohne.kosten_flug_eur"]) if n else 0, "€", 0)
    co2 = tr.add("CO₂", "Flüge × Energie je Flug × Strommix",
                 f"{n} × {de(p['drohne.energie_kwh_flug'], 1)} kWh × {de(p['co2.strom_kg_kwh'], 2)} kg/kWh",
                 n * p["drohne.energie_kwh_flug"] * p["co2.strom_kg_kwh"], "kg", 1)
    return {"Zeit (min)": zeit, "Kosten (€)": kosten, "CO₂ (kg)": co2, "umlauf_min": umlauf,
            "fluege": n, "trace": tr}


def heli(pk, p):
    tr = Trace("heli", "Helikopter", "Abrechnung nach Flugminuten inkl. An- und Abflug.")
    brutto = pk["brutto"]
    rot = tr.add("Rotationen", "⌈Bruttogewicht / Nutzlast je Rotation⌉",
                 f"⌈{de(brutto, 1)} kg / {de(p['heli.nutzlast_kg'])} kg⌉",
                 math.ceil(brutto / p["heli.nutzlast_kg"]) if brutto else 0, "", 0)
    minuten = tr.add("Flugminuten", "An- und Abflug + Rotationen × Dauer je Rotation",
                     f"{de(p['heli.anflug_min'])} + {rot} × {de(p['heli.rotation_min'])} min",
                     (p["heli.anflug_min"] + rot * p["heli.rotation_min"]) if rot else 0, "min", 0)
    kosten = tr.add("Kosten", "Flugminuten × Preis je Minute",
                    f"{de(minuten)} min × {de(p['heli.eur_min'])} €/min", minuten * p["heli.eur_min"], "€", 0)
    co2 = tr.add("CO₂", "Flugstunden × Verbrauch × Emissionsfaktor",
                 f"{de(minuten / 60, 2)} h × {de(p['heli.kerosin_l_h'])} l/h × {de(p['co2.kerosin_kg_l'], 2)} kg/l",
                 minuten / 60 * p["heli.kerosin_l_h"] * p["co2.kerosin_kg_l"], "kg", 1)
    return {"Zeit (min)": minuten, "Kosten (€)": kosten, "CO₂ (kg)": co2, "rotationen": rot, "trace": tr}


def manuell(prof, pk, job, p):
    tr = Trace("manuell", "Manueller Transport",
               "Das Team trägt die Fracht ohne Boxen. Höhenmeter kommen aus dem Geländeprofil "
               "(bergauf und bergab entlang der Luftlinie).")
    team, netto = job["team"], pk["netto"]
    gaenge = tr.add("Gänge", "⌈Nettogewicht / (Team × Traglast)⌉",
                    f"⌈{de(netto, 1)} kg / ({team} × {de(p['manuell.traglast_kg'])} kg)⌉",
                    math.ceil(netto / (team * p["manuell.traglast_kg"])) if netto else 0, "", 0)
    hm = prof["asc"] + prof["desc"]
    gang_h = tr.add("Zeit je Gang", "(↑ + ↓) / v_Aufstieg + (↑ + ↓) / v_Abstieg",
                    f"({de(prof['asc'])} + {de(prof['desc'])}) Hm / {de(p['manuell.aufstieg_hm_h'])} Hm/h + "
                    f"({de(prof['asc'])} + {de(prof['desc'])}) Hm / {de(p['manuell.abstieg_hm_h'])} Hm/h",
                    hm / p["manuell.aufstieg_hm_h"] + hm / p["manuell.abstieg_hm_h"], "h", 2,
                    kommentar="Hinweg mit Last, Rückweg ohne; Gegenanstiege zählen in beide Richtungen")
    zeit_h = gaenge * gang_h
    tr.add("Zeit gesamt", "Gänge × Zeit je Gang", f"{gaenge} × {de(gang_h, 2)} h", zeit_h, "h", 1)
    kosten = tr.add("Kosten", "Zeit × Team × Stundensatz",
                    f"{de(zeit_h, 2)} h × {team} × {de(p['manuell.stundensatz_eur_h'])} €/h",
                    zeit_h * team * p["manuell.stundensatz_eur_h"], "€", 0)
    return {"Zeit (min)": zeit_h * 60, "Kosten (€)": kosten, "CO₂ (kg)": 0.0, "gaenge": gaenge, "trace": tr}
