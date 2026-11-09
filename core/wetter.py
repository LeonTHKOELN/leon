"""Wetter am Einsatzort: Vorhersage (Open-Meteo), Flug-Ampel je Tag, Erntefenster für die Heuernte.

Quelle: Open-Meteo Forecast API (kostenlos, ohne Schlüssel, bis 16 Tage). Daten CC BY 4.0.
Wind in Flughöhe: stündlicher Wind in 80 m und 120 m über Grund, Maximum im Arbeitszeitraum.
Böen gibt es nur in 10 m Höhe. Die Ampel ist eine Planungshilfe, die Entscheidung trifft der Pilot.
"""
import requests

TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WMO = {  # Wettercode → (Symbol, Text)
    0: ("☀️", "klar"), 1: ("🌤️", "überwiegend klar"), 2: ("⛅", "teilweise bewölkt"), 3: ("☁️", "bedeckt"),
    45: ("🌫️", "Nebel"), 48: ("🌫️", "Reifnebel"), 51: ("🌦️", "leichter Niesel"), 53: ("🌦️", "Niesel"),
    55: ("🌦️", "starker Niesel"), 56: ("🌧️", "gefrierender Niesel"), 57: ("🌧️", "gefrierender Niesel"),
    61: ("🌧️", "leichter Regen"), 63: ("🌧️", "Regen"), 65: ("🌧️", "starker Regen"),
    66: ("🌧️", "gefrierender Regen"), 67: ("🌧️", "gefrierender Regen"), 71: ("🌨️", "leichter Schnee"),
    73: ("🌨️", "Schnee"), 75: ("🌨️", "starker Schnee"), 77: ("🌨️", "Schneegriesel"), 80: ("🌦️", "Regenschauer"),
    81: ("🌧️", "Regenschauer"), 82: ("⛈️", "heftige Schauer"), 85: ("🌨️", "Schneeschauer"),
    86: ("🌨️", "Schneeschauer"), 95: ("⛈️", "Gewitter"), 96: ("⛈️", "Gewitter mit Hagel"),
    99: ("⛈️", "Gewitter mit Hagel"),
}
DAILY = ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum",
         "precipitation_probability_max", "wind_speed_10m_max", "wind_gusts_10m_max", "sunshine_duration"]
HOURLY = ["wind_speed_80m", "wind_speed_120m"]


def fetch(lat, lon, hoehe_m=None, tage=16, arbeitszeit=(7, 19)):
    """Tagesvorhersage am Punkt. Rückgabe: Liste je Tag (fehlende Werte = None)."""
    params = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "daily": ",".join(DAILY),
              "hourly": ",".join(HOURLY), "wind_speed_unit": "ms", "timezone": "Europe/Berlin",
              "forecast_days": tage}
    if hoehe_m is not None:
        params["elevation"] = f"{hoehe_m:.0f}"
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=20)
    r.raise_for_status()
    js = r.json()
    d, h = js["daily"], js.get("hourly", {})
    # Wind in Flughöhe: Maximum je Tag im Arbeitszeitraum über 80 m und 120 m
    hoehenwind = {}
    for i, t in enumerate(h.get("time", [])):
        tag, stunde = t[:10], int(t[11:13])
        if not arbeitszeit[0] <= stunde <= arbeitszeit[1]:
            continue
        werte = [h[v][i] for v in HOURLY if h.get(v) and h[v][i] is not None]
        if werte:
            hoehenwind[tag] = max(hoehenwind.get(tag, 0), max(werte))
    out = []
    for i, tag in enumerate(d["time"]):
        def g(k):
            arr = d.get(k)
            return arr[i] if arr and i < len(arr) else None
        sonne = g("sunshine_duration")
        out.append({"datum": tag, "code": g("weather_code"), "tmax": g("temperature_2m_max"),
                    "tmin": g("temperature_2m_min"), "regen_mm": g("precipitation_sum"),
                    "regen_pct": g("precipitation_probability_max"), "wind10": g("wind_speed_10m_max"),
                    "boe": g("wind_gusts_10m_max"), "wind_hoehe": hoehenwind.get(tag),
                    "sonne_h": sonne / 3600 if sonne is not None else None})
    return out, js.get("elevation")


def flugampel(t, p):
    """Ampel für einen Flugtag: 'grün', 'gelb' oder 'rot' plus Gründe."""
    rot, gelb = [], []

    def pruef(wert, grenze, text, einheit):
        if wert is None:
            return
        if wert > grenze:
            rot.append(f"{text} {wert:.0f} {einheit} > {grenze:.0f}")
        elif wert > 0.8 * grenze:
            gelb.append(f"{text} {wert:.0f} {einheit} nahe Grenze")

    pruef(t["boe"], p["wetter.boe_max_ms"], "Böen", "m/s")
    pruef(t["wind_hoehe"] if t["wind_hoehe"] is not None else t["wind10"], p["wetter.wind_max_ms"],
          "Wind in Flughöhe" if t["wind_hoehe"] is not None else "Wind", "m/s")
    if t["regen_mm"] is not None and t["regen_mm"] > p["wetter.regen_max_mm"]:
        rot.append(f"Regen {t['regen_mm']:.1f} mm")
    elif t["regen_pct"] is not None and t["regen_pct"] >= 50:
        gelb.append(f"Regenrisiko {t['regen_pct']:.0f} %")
    if t["tmin"] is not None and t["tmin"] < p["wetter.temp_min_c"]:
        rot.append(f"Kälte {t['tmin']:.0f} °C (Akkus)")
    if t["code"] in (95, 96, 99):
        rot.append("Gewitter")
    if rot:
        return "rot", rot + gelb
    return ("gelb", gelb) if gelb else ("grün", [])


def trocken(t, p):
    """Guter Trocknungstag für Heu: wenig Regen und genug Sonne."""
    regen_ok = t["regen_mm"] is not None and t["regen_mm"] <= p["heu.trocknung_regen_max_mm"]
    sonne_ok = t["sonne_h"] is not None and t["sonne_h"] >= p["heu.trocknung_sonne_min_h"]
    return regen_ok and sonne_ok


def erntefenster(tage, p, trocknung_tage, max_vorschlaege=3):
    """Folgen Mähtag (flugtauglich) → Trocknungstage (trocken) → Erntetag (flugtauglich), beste zuerst.

    Bewertung: grüne Flugtage vor gelben, dann mehr Sonne während der Trocknung, dann früher Termin.
    """
    n, t = len(tage), max(0, int(trocknung_tage))
    kandidaten = []
    for i in range(n - t - 1):
        maeh, ernte = tage[i], tage[i + t + 1]
        a1, _ = flugampel(maeh, p)
        a2, _ = flugampel(ernte, p)
        if "rot" in (a1, a2):
            continue
        # Am Mähtag selbst soll es nach dem Mähen ebenfalls nicht regnen
        if maeh["regen_mm"] is not None and maeh["regen_mm"] > p["heu.trocknung_regen_max_mm"]:
            continue
        trock = tage[i + 1:i + t + 1]
        if not all(trocken(x, p) for x in trock):
            continue
        sonne = sum((x["sonne_h"] or 0) for x in [maeh] + trock)
        punkte = (a1 == "grün") + (a2 == "grün")
        kandidaten.append({"maehtag": maeh, "erntetag": ernte, "trocknung": trock, "ampel": (a1, a2),
                           "sonne_h": sonne, "score": (punkte, sonne, -i), "start_index": i})
    kandidaten.sort(key=lambda k: k["score"], reverse=True)
    return kandidaten[:max_vorschlaege]


def tagname(datum):
    from datetime import date
    d = date.fromisoformat(datum)
    return f"{TAGE[d.weekday()]} {d.day:02d}.{d.month:02d}."
