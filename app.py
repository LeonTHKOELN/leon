"""
Lift Planner
Konzeptprototyp TH Köln x STIHL: Planung von Drohnen-Materialtransporten in Steillagen.
Alle Werte sind Beispielwerte und in der Seitenleiste unter "Annahmen" anpassbar.
"""

import math

import altair as alt
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Lift Planner", page_icon="🟧", layout="wide")

ORANGE = "#FF6600"
ORANGE_DARK = "#E05A00"
ORANGE_LIGHT = "#FFF3EB"
INK = "#1F1F1F"
GREY_900 = "#2B2B2B"
GREY_600 = "#6B6B6B"
GREY_400 = "#A8A8A8"
GREY_200 = "#E6E6E6"
GREY_100 = "#F4F4F4"

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stMarkdown, .stTextInput, .stNumberInput, .stRadio, button {{
  font-family: "Barlow", Calibri, "Segoe UI", sans-serif !important;
}}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.6rem; padding-bottom: 2rem; max-width: 1240px; }}
section[data-testid="stSidebar"] {{ background: {GREY_100}; border-right: 1px solid {GREY_200}; }}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}
.sb-brand {{ display: flex; align-items: center; gap: 10px; margin: 4px 0 2px 0; }}
.sb-mark {{ width: 34px; height: 34px; background: {ORANGE}; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; color: #fff;
  font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 1.1rem; }}
.sb-name {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 1.45rem; color: {INK}; letter-spacing: .02em; }}
.sb-sub {{ color: {GREY_600}; font-size: .85rem; margin-bottom: 18px; }}
.sb-label {{ color: {GREY_600}; font-size: .72rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; margin: 6px 0 6px 2px; }}
section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 4px; align-items: stretch; width: 100%; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"], section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {{ width: 100%; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{
  display: flex !important; width: 100%; padding: 10px 12px; margin: 0; border-radius: 6px; border-left: 4px solid transparent;
  cursor: pointer; transition: background .15s;
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: #EAEAEA; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label p {{ font-size: 1rem; font-weight: 500; color: {GREY_900}; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] {{
  background: #FFFFFF; border-left-color: {ORANGE}; box-shadow: 0 1px 3px rgba(0,0,0,.06);
}}
section[data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] p {{ color: {ORANGE}; font-weight: 700; }}
.sb-foot {{ color: {GREY_400}; font-size: .78rem; margin-top: 28px; line-height: 1.5; }}
.lp-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
.lp-eyebrow {{ color: {ORANGE}; font-weight: 700; font-size: .78rem; letter-spacing: .16em; text-transform: uppercase; }}
.lp-h1 {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 2.6rem; color: {INK};
  line-height: 1.05; margin: 2px 0 4px 0; }}
.lp-lead {{ color: {GREY_600}; font-size: 1rem; }}
.lp-steps {{ display: flex; align-items: center; gap: 0; }}
.lp-step {{ display: flex; align-items: center; gap: 8px; color: {GREY_400}; font-weight: 600; font-size: .85rem; }}
.lp-step .dot {{ width: 26px; height: 26px; border-radius: 50%; border: 2px solid {GREY_200};
  display: flex; align-items: center; justify-content: center; font-size: .8rem; background: #fff; }}
.lp-step.done {{ color: {GREY_900}; }}
.lp-step.done .dot {{ border-color: {ORANGE}; color: {ORANGE}; }}
.lp-step.active {{ color: {INK}; }}
.lp-step.active .dot {{ background: {ORANGE}; border-color: {ORANGE}; color: #fff; }}
.lp-line {{ width: 28px; height: 2px; background: {GREY_200}; margin: 0 8px; }}
.lp-line.done {{ background: {ORANGE}; }}
.lp-rule {{ height: 3px; background: linear-gradient(90deg, {ORANGE} 0 90px, {GREY_200} 90px); margin-bottom: 24px; }}
.lp-card {{ background: #fff; border: 1px solid {GREY_200}; border-radius: 10px; padding: 18px 20px; }}
.lp-card-title {{ color: {GREY_600}; font-size: .74rem; font-weight: 700; letter-spacing: .14em;
  text-transform: uppercase; margin-bottom: 10px; }}
.lp-kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.lp-kpis.two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.lp-kpi {{ background: #fff; border: 1px solid {GREY_200}; border-radius: 10px; padding: 14px 16px; }}
.lp-kpi .k {{ color: {GREY_600}; font-size: .8rem; font-weight: 600; }}
.lp-kpi .v {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 2rem; color: {INK}; line-height: 1.1; white-space: nowrap; }}
.lp-kpi .v small {{ font-size: 1.1rem; color: {GREY_600}; margin-left: 3px; }}
.lp-kpi .s {{ color: {GREY_600}; font-size: .8rem; }}
.lp-kpi.accent {{ background: {ORANGE}; border-color: {ORANGE}; }}
.lp-kpi.accent .k, .lp-kpi.accent .s, .lp-kpi.accent .v small {{ color: rgba(255,255,255,.85); }}
.lp-kpi.accent .v {{ color: #fff; }}
.lp-route {{ display: grid; grid-template-columns: 22px 1fr auto; row-gap: 0; align-items: center; }}
.lp-route .pin {{ width: 14px; height: 14px; border-radius: 50%; border: 3px solid {ORANGE}; background: #fff; margin-left: 4px; }}
.lp-route .pin.fill {{ background: {ORANGE}; }}
.lp-route .seg {{ width: 2px; height: 34px; margin-left: 10px;
  background: repeating-linear-gradient({ORANGE} 0 5px, transparent 5px 9px); }}
.lp-route .name {{ font-weight: 600; color: {INK}; }}
.lp-route .alt {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; color: {GREY_900}; font-size: 1.15rem; }}
.lp-route .mid {{ color: {GREY_600}; font-size: .85rem; }}
.lp-note {{ display: flex; gap: 12px; align-items: flex-start; background: #fff; border: 1px solid {GREY_200};
  border-left: 4px solid {ORANGE}; border-radius: 8px; padding: 12px 16px; font-size: .92rem; color: {GREY_900}; }}
.lp-note .ic {{ color: {ORANGE}; font-weight: 700; font-size: 1.1rem; line-height: 1.2; }}
.lp-note.warn {{ background: {ORANGE_LIGHT}; }}
.lp-hero {{ background: {INK}; color: #fff; border-radius: 12px; padding: 22px 26px;
  display: flex; justify-content: space-between; align-items: center; gap: 20px; }}
.lp-hero .t {{ color: {GREY_400}; font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }}
.lp-hero .big {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 2.4rem; color: {ORANGE}; line-height: 1.1; }}
.lp-hero .sub {{ color: #DDD; font-size: .92rem; }}
.lp-hero .div {{ width: 1px; align-self: stretch; background: #444; }}
.lp-eq-name {{ font-weight: 700; color: {INK}; font-size: 1rem; line-height: 1.2; min-height: 2.4em; }}
.lp-chip {{ display: inline-block; background: {GREY_100}; color: {GREY_900}; border-radius: 99px;
  padding: 2px 10px; font-size: .78rem; font-weight: 600; margin: 2px 4px 2px 0; }}
.lp-chip.o {{ background: {ORANGE_LIGHT}; color: {ORANGE_DARK}; }}
.lp-flight {{ background: #fff; border: 1px solid {GREY_200}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }}
.lp-flight .hd {{ display: flex; justify-content: space-between; align-items: baseline; }}
.lp-flight .no {{ font-family: "Barlow Condensed", "Arial Narrow", sans-serif; font-weight: 700; font-size: 1.35rem; color: {INK}; }}
.lp-flight .no span {{ color: {ORANGE}; }}
.lp-flight .kg {{ font-weight: 600; color: {GREY_900}; }}
.lp-flight .kg small {{ color: {GREY_600}; font-weight: 500; }}
.lp-bar {{ background: {GREY_100}; height: 8px; border-radius: 4px; overflow: hidden; margin: 8px 0 10px 0; }}
.lp-bar > div {{ background: {ORANGE}; height: 8px; border-radius: 4px; }}
.lp-meta {{ color: {GREY_600}; font-size: .82rem; margin-top: 4px; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 10px !important; }}
.stButton > button {{ border-radius: 8px; font-weight: 600; padding: .55rem 1.2rem; }}
.stButton > button[kind="primary"] {{ background: {ORANGE}; border-color: {ORANGE}; }}
.stButton > button[kind="primary"]:hover {{ background: {ORANGE_DARK}; border-color: {ORANGE_DARK}; }}
iframe {{ border-radius: 10px; }}
.lp-footer {{ color: {GREY_400}; font-size: .78rem; border-top: 1px solid {GREY_200}; margin-top: 36px; padding-top: 10px; }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Stammdaten (Beispielwerte)
# ---------------------------------------------------------------------------
EQUIPMENT = [
    {"id": "ms", "name": "Motorsäge", "note": "Tank leer", "kg": 6.5, "default": 1},
    {"id": "fs", "name": "Freischneider", "note": "inkl. Schutz", "kg": 9.0, "default": 1},
    {"id": "eb", "name": "Erdbohrer", "note": "mit Bohrer", "kg": 10.0, "default": 1},
    {"id": "ht", "name": "Hochentaster", "note": "Teleskop", "kg": 7.0, "default": 0},
    {"id": "sw", "name": "Seilwinde", "note": "tragbar", "kg": 16.0, "default": 0},
    {"id": "zb", "name": "Zubehör", "note": "Ketten, Keile, Feilen", "kg": 9.0, "default": 1},
    {"id": "wz", "name": "Werkzeugkiste", "note": "Service", "kg": 12.0, "default": 0},
    {"id": "wv", "name": "Verpflegung", "note": "Wasser, Proviant", "kg": 6.0, "default": 1},
]

DEFAULTS = {
    "w_einsatz": "Hangpflege Silbertal",
    "w_start_name": "Landeplatz Tal",
    "w_start_lat": 47.0800, "w_start_lon": 9.9170, "w_start_alt": 920,
    "w_ziel_lat": 47.0890, "w_ziel_lon": 9.9330, "w_ziel_alt": 1340,
    "w_dauer": 8, "w_team": 2,
    "w_energie": "Akku-Lösung", "w_akkus": 6, "w_liter": 5.0,
    "w_payload": 80.0, "w_speed": 10.0, "w_climb": 3.0, "w_handling": 6.0,
    "w_box_tare": 4.0, "w_box_cap": 35.0, "w_dg_tare": 6.0, "w_net_tare": 2.0,
    "w_dg_separate": True,
    "w_drone_flat": 250.0, "w_drone_flight": 45.0, "w_kwh": 2.0, "w_grid": 0.10,
    "w_heli_eur_min": 38.0, "w_heli_payload": 600.0, "w_heli_anflug": 20.0,
    "w_heli_rot": 6.0, "w_heli_lh": 170.0,
    "w_carry_kg": 20.0, "w_up": 300.0, "w_down": 600.0, "w_wage": 35.0,
}
for e in EQUIPMENT:
    DEFAULTS[f"w_q_{e['id']}"] = e["default"]

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
for k in [k for k in st.session_state.keys() if str(k).startswith("w_")]:
    st.session_state[k] = st.session_state[k]

PAGES = ["Auftrag", "Ausrüstung", "Flugplan", "Einsparungen"]
st.session_state.setdefault("page", "Auftrag")
S = st.session_state


def go(page: str):
    st.session_state.page = page


# ---------------------------------------------------------------------------
# Berechnungen
# ---------------------------------------------------------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def first_fit(items, cap, weight_key):
    bins = []
    for it in sorted(items, key=lambda x: -x[weight_key]):
        for b in bins:
            if b["load"] + it[weight_key] <= cap + 1e-9:
                b["items"].append(it)
                b["load"] += it[weight_key]
                break
        else:
            bins.append({"items": [it], "load": it[weight_key]})
    return bins


def build_items():
    items = []
    for e in EQUIPMENT:
        for _ in range(int(S[f"w_q_{e['id']}"])):
            items.append({"name": e["name"], "kg": e["kg"], "dg": False})
    if S.w_energie in ("Akku-Lösung", "Beides"):
        for _ in range(int(S.w_akkus)):
            items.append({"name": "Akku", "kg": 1.6, "dg": True})
    if S.w_energie in ("Benzin-Lösung", "Beides") and S.w_liter > 0:
        items.append({"name": f"Kraftstoff {S.w_liter:g} l",
                      "kg": round(S.w_liter * 0.75 + 1.0, 1), "dg": True})
    return items


def build_units(items):
    units = []
    normal = [i for i in items if not i["dg"]]
    dg = [i for i in items if i["dg"]]
    oversize = [i for i in normal if i["kg"] > S.w_box_cap]
    normal = [i for i in normal if i["kg"] <= S.w_box_cap]
    for b in first_fit(normal, S.w_box_cap, "kg"):
        units.append({"typ": "Box", "items": b["items"], "netto": b["load"],
                      "brutto": b["load"] + S.w_box_tare, "dg": False})
    for b in first_fit(dg, S.w_box_cap, "kg"):
        units.append({"typ": "Gefahrgut-Box", "items": b["items"], "netto": b["load"],
                      "brutto": b["load"] + S.w_dg_tare, "dg": True})
    for i in oversize:
        units.append({"typ": "Lastnetz", "items": [i], "netto": i["kg"],
                      "brutto": i["kg"] + S.w_net_tare, "dg": False})
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for n, u in enumerate(units):
        u["label"] = f"{u['typ']} {letters[n % 26]}"
    return units


def build_flights(units):
    too_heavy = [u for u in units if u["brutto"] > S.w_payload]
    ok = [u for u in units if u["brutto"] <= S.w_payload]
    groups = [[u for u in ok if not u["dg"]], [u for u in ok if u["dg"]]] if S.w_dg_separate else [ok]
    flights = []
    for g in groups:
        for b in first_fit(g, S.w_payload, "brutto"):
            flights.append({"units": b["items"], "load": b["load"]})
    return flights, too_heavy


def compute():
    dist_m = haversine_m(S.w_start_lat, S.w_start_lon, S.w_ziel_lat, S.w_ziel_lon)
    dh = abs(S.w_ziel_alt - S.w_start_alt)
    items = build_items()
    units = build_units(items)
    flights, too_heavy = build_flights(units)
    oneway_min = (dist_m / S.w_speed + dh / S.w_climb) / 60
    flight_min = 2 * oneway_min + S.w_handling
    n = len(flights)
    netto = sum(i["kg"] for i in items)
    brutto = sum(u["brutto"] for u in units)
    drone = {"Zeit (min)": n * flight_min,
             "Kosten (€)": S.w_drone_flat + n * S.w_drone_flight if n else 0,
             "CO₂ (kg)": n * S.w_kwh * S.w_grid}
    rotations = math.ceil(brutto / S.w_heli_payload) if brutto else 0
    heli_min = S.w_heli_anflug + rotations * S.w_heli_rot if rotations else 0
    heli = {"Zeit (min)": heli_min, "Kosten (€)": heli_min * S.w_heli_eur_min,
            "CO₂ (kg)": heli_min / 60 * S.w_heli_lh * 2.52}
    trips = math.ceil(netto / (S.w_team * S.w_carry_kg)) if netto else 0
    carry_h = trips * (dh / S.w_up + dh / S.w_down)
    carry = {"Zeit (min)": carry_h * 60, "Kosten (€)": carry_h * S.w_team * S.w_wage, "CO₂ (kg)": 0.0}
    return {"dist_m": dist_m, "dh": dh, "items": items, "units": units, "flights": flights,
            "too_heavy": too_heavy, "flight_min": flight_min, "netto": netto, "brutto": brutto,
            "drone": drone, "heli": heli, "carry": carry, "rotations": rotations, "trips": trips,
            "has_dg": any(i["dg"] for i in items)}


# ---------------------------------------------------------------------------
# Formatierung und Bausteine
# ---------------------------------------------------------------------------
def de(x, nd=0):
    t = f"{x:,.{nd}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_min(m):
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def page_head(page: str, title: str, lead: str):
    idx = PAGES.index(page)
    steps = []
    for i, p in enumerate(PAGES):
        cls = "active" if i == idx else ("done" if i < idx else "")
        mark = "✓" if i < idx else str(i + 1)
        steps.append(f'<div class="lp-step {cls}"><div class="dot">{mark}</div>{p}</div>')
        if i < len(PAGES) - 1:
            steps.append(f'<div class="lp-line {"done" if i < idx else ""}"></div>')
    st.markdown(
        f"""<div class="lp-top"><div class="lp-eyebrow">Schritt {idx + 1} von 4 · {page}</div>
          <div class="lp-steps">{''.join(steps)}</div></div>
          <div class="lp-h1">{title}</div><div class="lp-lead">{lead}</div>
          <div class="lp-rule" style="margin-top:16px"></div>""",
        unsafe_allow_html=True,
    )


def kpi_html(k, v, unit="", s="", accent=False):
    return (f'<div class="lp-kpi {"accent" if accent else ""}"><div class="k">{k}</div>'
            f'<div class="v">{v}<small>{unit}</small></div><div class="s">{s}</div></div>')


def kpis(cards, two=False):
    st.markdown(f'<div class="lp-kpis {"two" if two else ""}">{"".join(cards)}</div>',
                unsafe_allow_html=True)


def note(text, warn=False, icon="i"):
    st.markdown(f'<div class="lp-note {"warn" if warn else ""}"><div class="ic">{icon}</div>'
                f'<div>{text}</div></div>', unsafe_allow_html=True)


def dg_note():
    note("<b>Gefahrgut an Bord.</b> Akkus und Kraftstoff gelten als Fracht als Gefahrgut. "
         "Flug nur in der Specific-Kategorie mit Betriebsgenehmigung. Einstufung im Einzelfall "
         "durch die Behörde (z. B. Austro Control) klären.", warn=True, icon="!")


def nav(prev_page=None, next_page=None, next_label="Weiter"):
    st.write("")
    c1, _, c3 = st.columns([1, 3, 1])
    if prev_page:
        c1.button("← Zurück", on_click=go, args=(prev_page,), width="stretch")
    if next_page:
        c3.button(f"{next_label} →", on_click=go, args=(next_page,), type="primary", width="stretch")


def section_title(t):
    st.markdown(f'<div class="lp-card-title" style="margin-top:6px">{t}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Seitenleiste
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """<div class="sb-brand"><div class="sb-mark">LP</div><div class="sb-name">LIFT PLANNER</div></div>
        <div class="sb-sub">Drohnenlogistik für Steillagen</div><div class="sb-label">Planung</div>""",
        unsafe_allow_html=True,
    )
    st.radio("Navigation", PAGES, key="page", label_visibility="collapsed",
             format_func=lambda p: f"{PAGES.index(p) + 1:02d}   {p}")
    st.markdown('<div class="sb-label" style="margin-top:22px">Einstellungen</div>', unsafe_allow_html=True)
    with st.expander("Annahmen (Beispielwerte)"):
        st.caption("Drohne und Box")
        st.number_input("Max. Nutzlast Drohne (kg)", 10.0, 200.0, step=5.0, key="w_payload")
        st.number_input("Reisegeschwindigkeit (m/s)", 2.0, 25.0, step=1.0, key="w_speed")
        st.number_input("Steigrate (m/s)", 0.5, 10.0, step=0.5, key="w_climb")
        st.number_input("Handling je Flug (min)", 0.0, 30.0, step=1.0, key="w_handling")
        st.number_input("Box Leergewicht (kg)", 0.0, 20.0, step=0.5, key="w_box_tare")
        st.number_input("Max. Zuladung je Box (kg)", 5.0, 100.0, step=1.0, key="w_box_cap")
        st.number_input("Gefahrgut-Box Leergewicht (kg)", 0.0, 20.0, step=0.5, key="w_dg_tare")
        st.number_input("Lastnetz Leergewicht (kg)", 0.0, 10.0, step=0.5, key="w_net_tare")
        st.checkbox("Gefahrgut in separaten Flügen", key="w_dg_separate")
        st.caption("Kosten Drohne (Dienstleister)")
        st.number_input("Einsatzpauschale (€)", 0.0, 5000.0, step=10.0, key="w_drone_flat")
        st.number_input("Kosten je Flug (€)", 0.0, 1000.0, step=5.0, key="w_drone_flight")
        st.number_input("Energie je Flug (kWh)", 0.0, 20.0, step=0.1, key="w_kwh")
        st.number_input("Strommix (kg CO₂/kWh)", 0.0, 1.0, step=0.01, key="w_grid")
        st.caption("Helikopter")
        st.number_input("Kosten je Flugminute (€)", 0.0, 200.0, step=1.0, key="w_heli_eur_min")
        st.number_input("Nutzlast je Rotation (kg)", 100.0, 2000.0, step=50.0, key="w_heli_payload")
        st.number_input("An- und Abflug (min)", 0.0, 120.0, step=5.0, key="w_heli_anflug")
        st.number_input("Dauer je Rotation (min)", 1.0, 30.0, step=1.0, key="w_heli_rot")
        st.number_input("Kerosinverbrauch (l/h)", 0.0, 500.0, step=10.0, key="w_heli_lh")
        st.caption("Tragen")
        st.number_input("Traglast je Person (kg)", 5.0, 40.0, step=1.0, key="w_carry_kg")
        st.number_input("Aufstieg mit Last (Hm/h)", 50.0, 800.0, step=10.0, key="w_up")
        st.number_input("Abstieg (Hm/h)", 100.0, 1500.0, step=10.0, key="w_down")
        st.number_input("Stundensatz (€/h)", 0.0, 200.0, step=1.0, key="w_wage")
    st.markdown('<div class="sb-foot">Konzeptprototyp<br>TH Köln × STIHL<br>Arbeiten in Steillagen</div>',
                unsafe_allow_html=True)

R = compute()
page = S.page

# ---------------------------------------------------------------------------
# 01 Auftrag
# ---------------------------------------------------------------------------
if page == "Auftrag":
    page_head("Auftrag", "Neuer Auftrag", "Einsatzort, Landeplatz und Team festlegen.")
    left, right = st.columns([7, 5], gap="large")
    with left:
        start = (S.w_start_lat, S.w_start_lon)
        ziel = (S.w_ziel_lat, S.w_ziel_lon)
        m = folium.Map(location=[(start[0] + ziel[0]) / 2, (start[1] + ziel[1]) / 2],
                       zoom_start=14, tiles=None, control_scale=True)
        folium.TileLayer(
            tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            attr='Karte: © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), '
                 '© OpenStreetMap-Mitwirkende', name="Topo", max_zoom=17,
        ).add_to(m)
        folium.PolyLine([start, ziel], color=ORANGE, weight=5, opacity=.95, dash_array="10 8").add_to(m)
        for pos, label, alt_m, fill in [(start, S.w_start_name, S.w_start_alt, "#FFFFFF"),
                                        (ziel, S.w_einsatz, S.w_ziel_alt, ORANGE)]:
            folium.CircleMarker(pos, radius=9, color=ORANGE, weight=4, fill=True,
                                fill_color=fill, fill_opacity=1).add_to(m)
            folium.Marker(pos, icon=folium.DivIcon(
                icon_size=(220, 30), icon_anchor=(-14, 14),
                html=f'<div style="font-family:Barlow,sans-serif;font-size:12px;font-weight:600;'
                     f'background:#fff;border-radius:4px;padding:3px 8px;display:inline-block;'
                     f'box-shadow:0 1px 4px rgba(0,0,0,.25);white-space:nowrap">'
                     f'{label} · {alt_m} m</div>')).add_to(m)
        m.fit_bounds([start, ziel], padding=(60, 60))
        st_folium(m, height=470, width="100%", returned_objects=[], key="map")
    with right:
        with st.container(border=True):
            section_title("Einsatz")
            st.text_input("Einsatzname", key="w_einsatz")
            c1, c2 = st.columns(2)
            c1.number_input("Einsatzdauer (h)", 1, 24, key="w_dauer")
            c2.number_input("Teamgröße", 1, 20, key="w_team")
        st.write("")
        st.markdown(
            f"""<div class="lp-card"><div class="lp-card-title">Route</div>
            <div class="lp-route">
              <div class="pin fill"></div><div class="name">{S.w_einsatz}</div><div class="alt">{S.w_ziel_alt} m</div>
              <div class="seg"></div><div class="mid">Luftlinie {de(R['dist_m'] / 1000, 1)} km ·
                Steigung {de((R['dh'] / R['dist_m'] * 100) if R['dist_m'] else 0)} %</div><div></div>
              <div class="pin"></div><div class="name">{S.w_start_name}</div><div class="alt">{S.w_start_alt} m</div>
            </div></div>""",
            unsafe_allow_html=True,
        )
        st.write("")
        kpis([kpi_html("Strecke", de(R["dist_m"] / 1000, 1), "km"),
              kpi_html("Höhe", f"+{de(R['dh'])}", "m"),
              kpi_html("Flugzeit", de(R["flight_min"]), "min", "je Umlauf")])

    st.write("")
    note(f"<b>Rollenmodell:</b> STIHL liefert Geräte und Transportboxen. Drohne, Pilot und Genehmigung "
         f"kommen vom Partner. Planungswert Nutzlast: <b>{de(S.w_payload)} kg</b> je Flug.")
    with st.expander("Koordinaten und Höhen bearbeiten"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Landeplatz (Start)**")
            st.text_input("Bezeichnung", key="w_start_name")
            st.number_input("Breitengrad", -90.0, 90.0, format="%.4f", step=0.001, key="w_start_lat")
            st.number_input("Längengrad", -180.0, 180.0, format="%.4f", step=0.001, key="w_start_lon")
            st.number_input("Höhe (m ü. NN)", 0, 5000, step=10, key="w_start_alt")
        with c2:
            st.markdown("**Einsatzort (Ziel)**")
            st.number_input("Breitengrad ", -90.0, 90.0, format="%.4f", step=0.001, key="w_ziel_lat")
            st.number_input("Längengrad ", -180.0, 180.0, format="%.4f", step=0.001, key="w_ziel_lon")
            st.number_input("Höhe (m ü. NN) ", 0, 5000, step=10, key="w_ziel_alt")
    nav(next_page="Ausrüstung")

# ---------------------------------------------------------------------------
# 02 Ausrüstung
# ---------------------------------------------------------------------------
elif page == "Ausrüstung":
    page_head("Ausrüstung", "Ausrüstung", "Geräte und Energieversorgung für den Einsatz wählen.")
    left, right = st.columns([8, 4], gap="large")
    with left:
        section_title("Geräte und Material")
        rows = [EQUIPMENT[:4], EQUIPMENT[4:]]
        for row in rows:
            cols = st.columns(4)
            for col, e in zip(cols, row):
                with col:
                    with st.container(border=True):
                        q = S[f"w_q_{e['id']}"]
                        chip = "lp-chip o" if q else "lp-chip"
                        st.markdown(f'<div class="lp-eq-name">{e["name"]}<br>'
                                    f'<span style="color:{GREY_600};font-weight:500;font-size:.82rem">{e["note"]}</span></div>'
                                    f'<span class="{chip}">{de(e["kg"], 1)} kg</span>',
                                    unsafe_allow_html=True)
                        st.number_input("Anzahl", 0, 20, key=f"w_q_{e['id']}", label_visibility="collapsed")
        st.write("")
        section_title("Energieversorgung")
        with st.container(border=True):
            st.radio("Energie", ["Akku-Lösung", "Benzin-Lösung", "Beides"], key="w_energie",
                     horizontal=True, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            if S.w_energie in ("Akku-Lösung", "Beides"):
                c1.number_input("Anzahl Akkus (je 1,6 kg)", 0, 40, key="w_akkus")
            if S.w_energie in ("Benzin-Lösung", "Beides"):
                c2.number_input("Kraftstoff (Liter)", 0.0, 50.0, step=0.5, key="w_liter")
    with right:
        section_title("Zusammenfassung")
        n_items = sum(1 for i in R["items"] if not i["dg"])
        dg_kg = sum(i["kg"] for i in R["items"] if i["dg"])
        st.markdown(kpi_html("Gesamtgewicht", de(R["netto"], 1), "kg", "ohne Transportboxen", accent=True),
                    unsafe_allow_html=True)
        st.write("")
        kpis([kpi_html("Teile", str(n_items), "", "Geräte und Material"),
              kpi_html("Gefahrgut", de(dg_kg, 1), "kg", "Akkus und Kraftstoff")], two=True)
        st.write("")
        if R["has_dg"]:
            dg_note()
        else:
            note("Kein Gefahrgut an Bord. Flug ohne Gefahrgut-Auflagen planbar.")
    nav(prev_page="Auftrag", next_page="Flugplan")

# ---------------------------------------------------------------------------
# 03 Flugplan
# ---------------------------------------------------------------------------
elif page == "Flugplan":
    page_head("Flugplan", "Flugplan", "Lasten werden automatisch in Boxen gepackt und auf Flüge verteilt.")
    if R["too_heavy"]:
        names = ", ".join(u["label"] for u in R["too_heavy"])
        note(f"<b>Zu schwer für die Drohne ({de(S.w_payload)} kg):</b> {names}. "
             "Nutzlast in den Annahmen erhöhen oder Last aufteilen.", warn=True, icon="!")
        st.write("")
    kpis([kpi_html("Flüge", str(len(R["flights"])), "", f"Nutzlast {de(S.w_payload)} kg", accent=True),
          kpi_html("Gesamtgewicht", de(R["brutto"]), "kg", "inkl. Boxen"),
          kpi_html("Gesamtzeit", fmt_min(len(R["flights"]) * R["flight_min"]), "", "inkl. Handling")])
    st.write("")
    left, right = st.columns([6, 6], gap="large")
    with left:
        section_title("Flüge")
        if not R["flights"]:
            note("Noch keine Ausrüstung gewählt.")
        for n, f in enumerate(R["flights"], 1):
            pct = min(f["load"] / S.w_payload * 100, 100)
            chips = "".join(f'<span class="lp-chip {"o" if u["dg"] else ""}">{u["label"]}</span>'
                            for u in f["units"])
            dg = ' · <span style="color:#E05A00;font-weight:700">Gefahrgut</span>' if any(u["dg"] for u in f["units"]) else ""
            st.markdown(
                f"""<div class="lp-flight"><div class="hd"><div class="no"><span>Flug</span> {n}</div>
                <div class="kg">{de(f['load'], 1)} kg <small>/ {de(S.w_payload)} kg</small></div></div>
                <div class="lp-bar"><div style="width:{pct:.0f}%"></div></div>{chips}
                <div class="lp-meta">≈ {fmt_min(R['flight_min'])} · {de(R['dist_m'] / 1000, 1)} km ·
                +{de(R['dh'])} m{dg}</div></div>""",
                unsafe_allow_html=True,
            )
        if R["has_dg"]:
            dg_note()
    with right:
        section_title("Packliste")
        if R["units"]:
            summary = pd.DataFrame([{"Einheit": u["label"], "Inhalt": ", ".join(i["name"] for i in u["items"]),
                                     "Netto kg": round(u["netto"], 1), "Brutto kg": round(u["brutto"], 1)}
                                    for u in R["units"]])
            st.dataframe(summary, hide_index=True, width="stretch",
                         column_config={"Inhalt": st.column_config.TextColumn(width="large")})
            rows = [{"Einheit": u["label"], "Inhalt": i["name"], "Gewicht (kg)": i["kg"],
                     "Gefahrgut": "ja" if i["dg"] else ""} for u in R["units"] for i in u["items"]]
            st.download_button("Packliste exportieren (CSV)",
                               pd.DataFrame(rows).to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name="packliste.csv", mime="text/csv", width="stretch")
    nav(prev_page="Ausrüstung", next_page="Einsparungen", next_label="Vergleich")

# ---------------------------------------------------------------------------
# 04 Einsparungen
# ---------------------------------------------------------------------------
elif page == "Einsparungen":
    page_head("Einsparungen", "Einsparungen", "Drohne im Vergleich zu Helikopter und Tragen für diesen Einsatz.")
    d, h, c = R["drone"], R["heli"], R["carry"]
    if R["flights"]:
        st.markdown(
            f"""<div class="lp-hero">
              <div><div class="t">Gegenüber Helikopter</div><div class="big">{de(h['Kosten (€)'] - d['Kosten (€)'])} €</div>
                <div class="sub">Kostendifferenz für diesen Einsatz</div></div><div class="div"></div>
              <div><div class="t">CO₂</div><div class="big">{de(h['CO₂ (kg)'] - d['CO₂ (kg)'])} kg</div>
                <div class="sub">weniger Emissionen als Heli</div></div><div class="div"></div>
              <div><div class="t">Gegenüber Tragen</div><div class="big">{de((c['Zeit (min)'] - d['Zeit (min)']) / 60, 1)} h</div>
                <div class="sub">Zeitdifferenz für {S.w_team} Personen</div></div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.write("")
    kpis([kpi_html("Drohne", str(len(R["flights"])), " Flüge",
                   f"{fmt_min(d['Zeit (min)'])} · {de(d['Kosten (€)'])} € · {de(d['CO₂ (kg)'], 1)} kg CO₂", accent=True),
          kpi_html("Helikopter", str(R["rotations"]), " Rot.",
                   f"{fmt_min(h['Zeit (min)'])} · {de(h['Kosten (€)'])} € · {de(h['CO₂ (kg)'])} kg CO₂"),
          kpi_html("Tragen", str(R["trips"]), " Gänge",
                   f"{fmt_min(c['Zeit (min)'])} · {de(c['Kosten (€)'])} € · {S.w_team} Personen")])
    st.write("")

    df = pd.DataFrame([{"Variante": "Drohne", **d}, {"Variante": "Helikopter", **h}, {"Variante": "Tragen", **c}])
    for mcol, nd_ in [("Kosten (€)", 0), ("Zeit (min)", 0), ("CO₂ (kg)", 1)]:
        df[mcol + " txt"] = df[mcol].apply(lambda v, n=nd_: de(v, n))
    color = alt.Scale(domain=["Drohne", "Helikopter", "Tragen"], range=[ORANGE, GREY_400, GREY_900])
    cols = st.columns(3, gap="medium")
    for col, (metric, label, nd) in zip(cols, [("Kosten (€)", "Kosten in €", 0),
                                               ("Zeit (min)", "Zeit in Minuten", 0),
                                               ("CO₂ (kg)", "CO₂ in kg", 1)]):
        with col:
            with st.container(border=True):
                section_title(label)
                base = alt.Chart(df).encode(
                    x=alt.X("Variante:N", sort=None, title=None,
                            axis=alt.Axis(labelAngle=0, labelFontSize=12, labelColor=GREY_900, ticks=False, domain=False)),
                    y=alt.Y(f"{metric}:Q", title=None, axis=None,
                            scale=alt.Scale(domainMax=max(df[metric].max() * 1.18, 1))),
                )
                bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=46).encode(
                    color=alt.Color("Variante:N", scale=color, legend=None),
                    tooltip=["Variante", alt.Tooltip(f"{metric}:Q", format=",.1f")])
                text = base.mark_text(dy=-9, fontSize=13, fontWeight=700, color=INK, font="Barlow, Arial, sans-serif").encode(
                    text=alt.Text(f"{metric} txt:N"))
                chart = (bars + text).properties(height=230).configure_view(stroke=None) \
                    .configure_axis(labelFont="Barlow, Arial, sans-serif", grid=False)
                st.altair_chart(chart, width="stretch")
    st.write("")
    note("Alle Werte sind Beispielwerte. Für das Nutzenversprechen in Sprint 7 die Annahmen in der "
         "Seitenleiste durch Werte aus den Interviews ersetzen (Heli-Kosten, Tragezeiten, Lasten).")
    if R["has_dg"]:
        st.write("")
        dg_note()
    nav(prev_page="Flugplan")

st.markdown(
    "<div class='lp-footer'>Konzeptprototyp · TH Köln × STIHL · Projekt Arbeiten in Steillagen · "
    "Alle Werte sind Beispielwerte und ersetzen keine Flugplanung oder behördliche Genehmigung.</div>",
    unsafe_allow_html=True,
)
