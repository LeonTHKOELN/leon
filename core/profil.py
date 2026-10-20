"""Flugprofil: geplante Flughöhe, Flugweg und Flugzeit aus dem Geländeprofil."""
import math

from .fmt import de
from .trace import Trace


def linear_terrain(ds, h_start, h_ziel):
    """Ersatzprofil ohne Höhenmodell: gerade Verbindung zwischen zwei Höhen."""
    n = len(ds) - 1
    return [h_start + (h_ziel - h_start) * i / n for i in range(n + 1)]


def _leg_seconds(seq, p, clear):
    """Flugzeit eines Weges. Je Abschnitt begrenzt das Langsamste: horizontal, Steigen oder Sinken."""
    v, vs, vd = p["drohne.v_reise_ms"], p["drohne.steigrate_ms"], p["drohne.sinkrate_ms"]
    t = clear / vs + clear / vd  # Start auf Flughöhe steigen, am Ziel landen
    for (d0, h0), (d1, h1) in zip(seq, seq[1:]):
        dz = h1 - h0
        tv = dz / vs if dz > 0 else -dz / vd
        t += max(abs(d1 - d0) / v, tv)
    return t


def build_profile(start, ziel, dist, pts, ds, step_eff, terrain, source, real, error, p):
    clear = float(p["profil.min_agl_m"])
    ceiling = max(float(p["profil.max_agl_m"]), clear)
    n = len(ds)
    tr = Trace("profil", "Flugprofil und Flugzeit",
               "Aus dem Geländeprofil entlang der Luftlinie wird eine Flughöhe im Korridor über Grund "
               "geplant. Daraus folgen Flugweg und Flugzeit je Richtung.")

    tr.add("Luftlinie", "d = Großkreisentfernung (Haversine)",
           f"({de(start[0], 5)}, {de(start[1], 5)}) → ({de(ziel[0], 5)}, {de(ziel[1], 5)})",
           dist / 1000, "km", 3)
    tr.add("Stützpunkte", "n = ⌈d / Raster⌉ + 1",
           f"⌈{de(dist)} m / {de(p['profil.raster_m'])} m⌉ + 1", n, "Punkte", 0,
           kommentar=f"tatsächlicher Abstand {de(step_eff, 1)} m · Höhenquelle: {source}")
    tr.add("Höhe Start / Ziel", "h aus Höhenmodell am ersten / letzten Punkt",
           source, 0, text=f"{de(terrain[0])} m / {de(terrain[-1])} m")

    z0, z1 = terrain[0] + clear, terrain[-1] + clear
    direct = [z0 + (z1 - z0) * (d / dist if dist else 0) for d in ds]
    path = [min(max(direct[i], terrain[i] + clear), terrain[i] + ceiling) for i in range(n)]
    tr.add("Geplante Flughöhe", "h(x) = min( max(Direktlinie(x), Gelände(x) + AGLmin), Gelände(x) + AGLmax )",
           f"AGLmin = {de(clear)} m · AGLmax = {de(ceiling)} m", 0,
           text=f"{de(min(path))} bis {de(max(path))} m ü. NN",
           kommentar="Direktlinie verbindet Start und Ziel jeweils AGLmin über Grund")

    flight_len = 2 * clear + sum(math.hypot(ds[i + 1] - ds[i], path[i + 1] - path[i]) for i in range(n - 1))
    tr.add("Flugweg je Richtung", "s = 2 · AGLmin + Σ √(Δx² + Δh²)",
           f"2 · {de(clear)} m + Summe über {n - 1} Abschnitte", flight_len / 1000, "km", 2,
           kommentar="Senkrechter Start und Landung plus Weg entlang der Flughöhe")

    seq = list(zip(ds, path))
    out_s, back_s = _leg_seconds(seq, p, clear), _leg_seconds(seq[::-1], p, clear)
    tr.add("Flugzeit Hinflug", "t = AGLmin/v_steig + AGLmin/v_sink + Σ max(Δx/v, Δh↑/v_steig, Δh↓/v_sink)",
           f"v = {de(p['drohne.v_reise_ms'], 1)} m/s · v_steig = {de(p['drohne.steigrate_ms'], 1)} m/s · "
           f"v_sink = {de(p['drohne.sinkrate_ms'], 1)} m/s", out_s / 60, "min", 1)
    tr.add("Flugzeit Rückflug", "wie Hinflug, Profil in Gegenrichtung", "", back_s / 60, "min", 1)

    slopes = [abs(terrain[i + 1] - terrain[i]) / (ds[i + 1] - ds[i]) * 100
              for i in range(n - 1) if ds[i + 1] > ds[i]]
    i_top = max(range(n), key=lambda i: terrain[i])
    return {
        "dist": dist, "ds": ds, "pts": pts, "terrain": terrain, "path": path, "direct": direct,
        "source": source, "error": error, "real": real, "step_eff": step_eff, "n": n,
        "start_alt": terrain[0], "ziel_alt": terrain[-1], "dh": terrain[-1] - terrain[0],
        "top_alt": terrain[i_top], "top_pt": pts[i_top], "top_d": ds[i_top],
        "top_is_end": i_top in (0, n - 1),
        "direct_min_agl": min(direct[i] - terrain[i] for i in range(n)),
        "direct_max_agl": max(direct[i] - terrain[i] for i in range(n)),
        "path_climb": sum(max(path[i + 1] - path[i], 0) for i in range(n - 1)),
        "max_slope": max(slopes) if slopes else 0,
        "out_min": out_s / 60, "back_min": back_s / 60,
        "flight_len": flight_len,
        "terrain_len": sum(math.hypot(ds[i + 1] - ds[i], terrain[i + 1] - terrain[i]) for i in range(n - 1)),
        "asc": sum(max(terrain[i + 1] - terrain[i], 0) for i in range(n - 1)),
        "desc": sum(max(terrain[i] - terrain[i + 1], 0) for i in range(n - 1)),
        "clear": clear, "ceiling": ceiling, "trace": tr,
    }
