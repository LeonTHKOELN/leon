"""Use Case Heuernte: Wiese, Heumenge, Heusammelsack, Ablauf über mehrere Tage.

Ablauf
  Tag 1          Mähen. Freischneider und Akkus hoch, abends wieder runter.
  Tag 2 … n      Trocknung (Anzahl Tage als Parameter). Keine Flüge.
  Erntetag       Laubbläser und leere Säcke hoch, Heu zusammenblasen, Säcke befüllen,
                 beladen ins Tal fliegen (Hang → Tal), leer zurück, zum Schluss Geräte runter.

Last je Heuflug = kleinerer Wert aus Nutzlast und Sackvolumen × Heudichte.
Säcke im Umlauf: Reichen sie für mindestens zwei Flüge, arbeiten Team (befüllen) und Drohne (fliegen)
parallel, sonst nacheinander.
"""
import math

from .fmt import de, fmt_min
from .trace import Trace

R_EARTH = 6_371_000


# ---------------------------------------------------------------------------
# Geometrie der Wiese
# ---------------------------------------------------------------------------
def _xy(lat0, lon0):
    """Lokale ebene Projektion (Meter) um einen Bezugspunkt. Für Flächen bis wenige km² ausreichend genau."""
    kx = math.radians(1) * R_EARTH * math.cos(math.radians(lat0))
    ky = math.radians(1) * R_EARTH
    return lambda lat, lon: ((lon - lon0) * kx, (lat - lat0) * ky), lambda x, y: (lat0 + y / ky, lon0 + x / kx)


def wiese_geometrie(poly):
    """poly: [(lat, lon), …] ohne Wiederholung des ersten Punkts. Rückgabe Fläche m², Schwerpunkt, Umfang."""
    if len(poly) < 3:
        raise ValueError("Wiese braucht mindestens drei Eckpunkte")
    lat0 = sum(p[0] for p in poly) / len(poly)
    lon0 = sum(p[1] for p in poly) / len(poly)
    to_xy, to_ll = _xy(lat0, lon0)
    pts = [to_xy(*p) for p in poly]
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    a /= 2
    if abs(a) < 1e-6:
        raise ValueError("Wiese hat keine Fläche")
    cx, cy = cx / (6 * a), cy / (6 * a)
    umfang = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
    return {"flaeche_m2": abs(a), "schwerpunkt": to_ll(cx, cy), "umfang_m": umfang, "punkte": poly}


def _inside(x, y, pts):
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def raster_in_wiese(poly, max_punkte=150):
    """Gleichmäßiges Raster innerhalb der Wiese für die Höhenabfrage. Abstand passt sich der Fläche an."""
    g = wiese_geometrie(poly)
    lat0, lon0 = g["schwerpunkt"]
    to_xy, to_ll = _xy(lat0, lon0)
    pts = [to_xy(*p) for p in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    abstand = max(15.0, math.sqrt(g["flaeche_m2"] / max_punkte))
    out = []
    y = min(ys) + abstand / 2
    while y < max(ys):
        x = min(xs) + abstand / 2
        while x < max(xs):
            if _inside(x, y, pts):
                out.append((x, y))
            x += abstand
        y += abstand
    if len(out) < 3:  # sehr kleine oder schmale Wiese: Eckpunkte und Schwerpunkt verwenden
        out = pts + [(0.0, 0.0)]
    return [to_ll(x, y) for x, y in out], out, abstand


def neigung(xy, z):
    """Mittlere Hangneigung über eine Ausgleichsebene z = a·x + b·y + c (kleinste Quadrate)."""
    n = len(xy)
    sx = sum(p[0] for p in xy) / n
    sy = sum(p[1] for p in xy) / n
    sz = sum(z) / n
    sxx = sum((p[0] - sx) ** 2 for p in xy)
    syy = sum((p[1] - sy) ** 2 for p in xy)
    sxy = sum((p[0] - sx) * (p[1] - sy) for p in xy)
    sxz = sum((p[0] - sx) * (zz - sz) for p, zz in zip(xy, z))
    syz = sum((p[1] - sy) * (zz - sz) for p, zz in zip(xy, z))
    det = sxx * syy - sxy ** 2
    if abs(det) < 1e-9:
        return 0.0, 0.0
    a = (sxz * syy - syz * sxy) / det
    b = (syz * sxx - sxz * sxy) / det
    g = math.hypot(a, b)
    return g * 100, math.degrees(math.atan(g))


# ---------------------------------------------------------------------------
# Heuernte rechnen
# ---------------------------------------------------------------------------
def heuernte(p, job, wiese, umlauf_min):
    """wiese: Ergebnis von wiese_geometrie, ergänzt um neigung_pct/neigung_grad/h_min/h_max/hoehen_quelle."""
    tr = Trace("heu", "Heuernte",
               "Heumenge aus Fläche und Ertrag, Last je Flug aus Nutzlast und Sackvolumen, Arbeitszeiten aus "
               "Flächenleistungen. Das Team arbeitet parallel zur Drohne, wenn genug Säcke im Umlauf sind.")
    team = job["team"]
    ha = tr.add("Fläche", "Polygonfläche (Gauß'sche Trapezformel, lokal eben)",
                f"{len(wiese['punkte'])} Eckpunkte", wiese["flaeche_m2"] / 10_000, "ha", 2)
    tr.add("Hangneigung", "Ausgleichsebene über Höhenraster der Wiese", wiese.get("hoehen_quelle", ""),
           wiese.get("neigung_pct", 0), "%", 0,
           kommentar=f"{de(wiese.get('neigung_grad', 0))}° · Höhe {de(wiese.get('h_min', 0))} bis "
                     f"{de(wiese.get('h_max', 0))} m")
    heu = tr.add("Heumenge", "Fläche × Ertrag", f"{de(ha, 2)} ha × {de(p['heu.ertrag_kg_ha'])} kg/ha",
                 ha * p["heu.ertrag_kg_ha"], "kg", 0)

    nutz, leer = p["drohne.nutzlast_kg"], p["sack.leergewicht_kg"]
    vol_kg = p["sack.volumen_m3"] * p["heu.dichte_kg_m3"]
    je_sack = tr.add("Heu je Sack", "min(Sackvolumen × Heudichte, Nutzlast − Sack leer)",
                     f"min({de(p['sack.volumen_m3'], 2)} m³ × {de(p['heu.dichte_kg_m3'])} kg/m³, "
                     f"{de(nutz)} − {de(leer, 1)} kg)", max(min(vol_kg, nutz - leer), 0), "kg", 1,
                     kommentar="begrenzt durch " + ("Volumen" if vol_kg < nutz - leer else "Nutzlast"))
    if je_sack <= 0:
        tr.add("Fehler", "Sack leer ist schwerer als die Nutzlast", "", 0, text="keine Heuflüge möglich")
        return {"ok": False, "trace": tr, "flaeche_ha": ha, "heu_kg": heu}
    je_flug = tr.add("Säcke je Flug", "⌊Nutzlast / (Heu je Sack + Sack leer)⌋, mindestens 1",
                     f"⌊{de(nutz)} / ({de(je_sack, 1)} + {de(leer, 1)})⌋",
                     max(1, math.floor(nutz / (je_sack + leer))), "", 0)
    fuellungen = tr.add("Sackfüllungen", "⌈Heumenge / Heu je Sack⌉", f"⌈{de(heu)} / {de(je_sack, 1)}⌉",
                        math.ceil(heu / je_sack) if heu else 0, "", 0)
    fluege = tr.add("Heuflüge", "⌈Sackfüllungen / Säcke je Flug⌉", f"⌈{fuellungen} / {je_flug}⌉",
                    math.ceil(fuellungen / je_flug) if fuellungen else 0, "", 0)
    last = je_flug * (je_sack + leer)
    tr.add("Last je Heuflug", "Säcke je Flug × (Heu je Sack + Sack leer)",
           f"{je_flug} × ({de(je_sack, 1)} + {de(leer, 1)}) kg", last, "kg", 1,
           kommentar="Richtung Hang → Tal beladen, Tal → Hang leer")

    maeh_h = tr.add("Mähzeit", "Fläche / (Mähleistung × Team)",
                    f"{de(ha, 2)} ha / ({de(p['heu.maehleistung_ha_h'], 2)} ha/h × {team})",
                    ha / (p["heu.maehleistung_ha_h"] * team), "h", 1)
    blas_h = tr.add("Zusammenblasen", "Fläche / (Blasleistung × Team)",
                    f"{de(ha, 2)} ha / ({de(p['heu.blasleistung_ha_h'], 2)} ha/h × {team})",
                    ha / (p["heu.blasleistung_ha_h"] * team), "h", 1)
    fuell_h = tr.add("Befüllen gesamt", "Sackfüllungen × Befüllzeit je Sack (Team)",
                     f"{fuellungen} × {de(p['sack.befuellzeit_min'])} min", fuellungen * p["sack.befuellzeit_min"] / 60,
                     "h", 1)
    flug_h = tr.add("Heuflüge gesamt", "Heuflüge × Zeit je Umlauf", f"{fluege} × {de(umlauf_min, 1)} min",
                    fluege * umlauf_min / 60, "h", 1)
    saecke = int(p["sack.anzahl"])
    parallel = saecke >= 2 * je_flug
    erster = je_flug * p["sack.befuellzeit_min"] / 60
    if parallel:
        ernte_h = tr.add("Erntezeit", "Blasen + max(Befüllen, Heuflüge) + Befüllen des ersten Flugs",
                         f"{de(blas_h, 1)} + max({de(fuell_h, 1)}, {de(flug_h, 1)}) + {de(erster, 2)} h",
                         blas_h + max(fuell_h, flug_h) + erster, "h", 1,
                         kommentar=f"{saecke} Säcke im Umlauf: Team und Drohne arbeiten parallel · Engpass: "
                                   + ("Team (Befüllen)" if fuell_h > flug_h else "Drohne (Flüge)"))
    else:
        ernte_h = tr.add("Erntezeit", "Blasen + Befüllen + Heuflüge (nacheinander)",
                         f"{de(blas_h, 1)} + {de(fuell_h, 1)} + {de(flug_h, 1)} h", blas_h + fuell_h + flug_h, "h", 1,
                         kommentar=f"Nur {saecke} Säcke: reicht nicht für parallele Arbeit, Team und Drohne warten "
                                   "aufeinander")
    arbeitstag = job["dauer_h"]
    maeh_tage = max(1, math.ceil(maeh_h / arbeitstag))
    ernte_tage = max(1, math.ceil(ernte_h / arbeitstag))
    trock = int(p["heu.trocknung_tage"])
    ablauf = []
    for i in range(maeh_tage):
        ablauf.append({"Tag": len(ablauf) + 1, "Phase": "Mähen", "Dauer h": min(arbeitstag, maeh_h - i * arbeitstag),
                       "Drohne": "Freischneider und Akkus hoch, abends runter"})
    for _ in range(trock):
        ablauf.append({"Tag": len(ablauf) + 1, "Phase": "Trocknung", "Dauer h": 0.0, "Drohne": "keine Flüge"})
    for i in range(ernte_tage):
        ablauf.append({"Tag": len(ablauf) + 1, "Phase": "Ernte", "Dauer h": min(arbeitstag, ernte_h - i * arbeitstag),
                       "Drohne": f"{fluege} Heuflüge ins Tal" if i == 0 else "Fortsetzung Heuflüge"})
    tr.add("Ablauf", "Mähtage + Trocknungstage + Erntetage",
           f"{maeh_tage} + {trock} + {ernte_tage} bei {de(arbeitstag)} h Arbeitszeit je Tag", len(ablauf), "Tage", 0,
           kommentar="Trocknung wetterabhängig, Anzahl Tage unter Annahmen & Parameter")
    return {"ok": True, "trace": tr, "flaeche_ha": ha, "heu_kg": heu, "je_sack": je_sack, "je_flug": je_flug,
            "fuellungen": fuellungen, "fluege": fluege, "last": last, "maeh_h": maeh_h, "blas_h": blas_h,
            "fuell_h": fuell_h, "flug_h": flug_h, "ernte_h": ernte_h, "parallel": parallel,
            "maeh_tage": maeh_tage, "ernte_tage": ernte_tage, "trocknung_tage": trock, "ablauf": ablauf,
            "engpass": ("Team" if fuell_h > flug_h else "Drohne") if parallel else "keiner (nacheinander)",
            "dauer_text": fmt_min(ernte_h * 60)}
