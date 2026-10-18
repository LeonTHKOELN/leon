"""
Lift Planner
Konzeptprototyp TH Köln x STIHL: Planung von Drohnen-Materialtransporten in Steillagen.
Alle Werte sind Beispielwerte und in der Seitenleiste unter "Annahmen" anpassbar.
"""

import math

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Lift Planner", page_icon="🪂", layout="wide")

ORANGE = "#FF6600"
ORANGE_LIGHT = "#FFF1E8"
GREY_BG = "#F2F2F2"
GREY_MID = "#9A9A9A"
DARK = "#1A1A1A"

# ---------------------------------------------------------------------------
# Styling (STIHL Light Theme)
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
html, body, [class*="css"] {{ font-family: Calibri, "Segoe UI", Arial, sans-serif; }}
.block-container {{ padding-top: 1.2rem; max-width: 1250px; }}
.lp-header {{
  background: {GREY_BG}; border-left: 10px solid {ORANGE};
  padding: 14px 22px; margin-bottom: 6px; display: flex;
  justify-content: space-between; align-items: center;
}}
.lp-title {{ font-size: 1.9rem; margin: 0; color: {DARK}; font-weight: 700; line-height: 1.2; }}
.lp-title span {{ color: {ORANGE}; }}
.lp-tag {{ color: {ORANGE}; font-weight: 700; font-size: 0.95rem; letter-spacing: .04em; }}
.lp-kicker {{
  color: {ORANGE}; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  font-size: .85rem; border-bottom: 3px solid {ORANGE}; display: inline-block;
  padding-bottom: 4px; margin: 10px 0 14px 0;
}}
.lp-card {{
  background: #FFFFFF; border: 1px solid #E3E3E3; border-radius: 6px;
  padding: 14px 16px; height: 100%;
}}
.lp-card h4 {{ color: {ORANGE}; margin: 0 0 6px 0; padding: 0; font-size: 1.0rem; hyphens: auto; }}
.lp-kpi {{ font-size: 1.9rem; font-weight: 700; color: {DARK}; line-height: 1.1; }}
.lp-kpi.orange {{ color: {ORANGE}; }}
.lp-sub {{ color: #666; font-size: .85rem; }}
.lp-banner {{
  background: {ORANGE}; color: white; border-radius: 6px; padding: 14px 18px;
  font-size: 1.05rem; margin-top: 8px;
}}
.lp-warn {{
  background: {ORANGE_LIGHT}; border-left: 5px solid {ORANGE}; border-radius: 4px;
  padding: 10px 14px; margin: 8px 0; font-size: .92rem;
}}
.lp-flight {{
  border: 1px solid #E3E3E3; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px;
}}
.lp-bar {{ background: #EEE; height: 10px; border-radius: 5px; overflow: hidden; margin: 6px 0; }}
.lp-bar > div {{ background: {ORANGE}; height: 10px; }}
.lp-footer {{ color: #888; font-size: .8rem; border-top: 1px solid #E3E3E3; margin-top: 30px; padding-top: 8px; }}
section[data-testid="stSidebar"] {{ background: {GREY_BG}; }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Stammdaten (Beispielwerte)
# ---------------------------------------------------------------------------
EQUIPMENT = [
    {"id": "ms", "name": "Motorsäge (Tank leer)", "kg": 6.5, "default": 1},
    {"id": "fs", "name": "Freischneider", "kg": 9.0, "default": 1},
    {"id": "eb", "name": "Erdbohrer", "kg": 10.0, "default": 1},
    {"id": "ht", "name": "Hochentaster", "kg": 7.0, "default": 0},
    {"id": "sw", "name": "Seilwinde (tragbar)", "kg": 16.0, "default": 0},
    {"id": "zb", "name": "Zubehör (Ketten, Keile, Feilen)", "kg": 9.0, "default": 1},
    {"id": "wz", "name": "Werkzeugkiste", "kg": 12.0, "default": 0},
    {"id": "wv", "name": "Wasser und Verpflegung", "kg": 6.0, "default": 1},
]

DEFAULTS = {
    # Auftrag
    "w_einsatz": "Hangpflege Silbertal",
    "w_start_name": "Landeplatz Tal",
    "w_start_lat": 47.0800, "w_start_lon": 9.9170, "w_start_alt": 920,
    "w_ziel_lat": 47.0890, "w_ziel_lon": 9.9330, "w_ziel_alt": 1340,
    "w_dauer": 8, "w_team": 2,
    # Energie
    "w_energie": "Akku-Lösung", "w_akkus": 6, "w_liter": 5.0,
    # Annahmen Drohne
    "w_payload": 80.0, "w_speed": 10.0, "w_climb": 3.0, "w_handling": 6.0,
    "w_box_tare": 4.0, "w_box_cap": 35.0, "w_dg_tare": 6.0, "w_net_tare": 2.0,
    "w_dg_separate": True,
    "w_drone_flat": 250.0, "w_drone_flight": 45.0, "w_kwh": 2.0, "w_grid": 0.10,
    # Annahmen Heli
    "w_heli_eur_min": 38.0, "w_heli_payload": 600.0, "w_heli_anflug": 20.0,
    "w_heli_rot": 6.0, "w_heli_lh": 170.0,
    # Annahmen Tragen
    "w_carry_kg": 20.0, "w_up": 300.0, "w_down": 600.0, "w_wage": 35.0,
}
for e in EQUIPMENT:
    DEFAULTS[f"w_q_{e['id']}"] = e["default"]

for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
# Widget-Werte über Seitenwechsel hinweg erhalten
for k in [k for k in st.session_state.keys() if str(k).startswith("w_")]:
    st.session_state[k] = st.session_state[k]
st.session_state.setdefault("page", "Auftrag")

PAGES = ["Auftrag", "Ausrüstung", "Flugplan", "Einsparungen"]
ICONS = {"Auftrag": "📍", "Ausrüstung": "🧰", "Flugplan": "🛫", "Einsparungen": "📉"}
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
        items.append({"name": f"Kraftstoff {S.w_liter:g} l (Kanister)",
                      "kg": round(S.w_liter * 0.75 + 1.0, 1), "dg": True})
    return items


def build_units(items):
    """Packt Gegenstände in Boxen. Gefahrgut kommt immer in eine eigene Gefahrgut-Box."""
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
    if S.w_dg_separate:
        groups = [[u for u in ok if not u["dg"]], [u for u in ok if u["dg"]]]
    else:
        groups = [ok]
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

    drone = {
        "Zeit (min)": n * flight_min,
        "Kosten (€)": S.w_drone_flat + n * S.w_drone_flight if n else 0,
        "CO₂ (kg)": n * S.w_kwh * S.w_grid,
    }
    rotations = math.ceil(brutto / S.w_heli_payload) if brutto else 0
    heli_min = S.w_heli_anflug + rotations * S.w_heli_rot if rotations else 0
    heli = {
        "Zeit (min)": heli_min,
        "Kosten (€)": heli_min * S.w_heli_eur_min,
        "CO₂ (kg)": heli_min / 60 * S.w_heli_lh * 2.52,
    }
    trips = math.ceil(netto / (S.w_team * S.w_carry_kg)) if netto else 0
    trip_h = dh / S.w_up + dh / S.w_down
    carry_h = trips * trip_h
    carry = {
        "Zeit (min)": carry_h * 60,
        "Kosten (€)": carry_h * S.w_team * S.w_wage,
        "CO₂ (kg)": 0.0,
    }
    return {
        "dist_m": dist_m, "dh": dh, "items": items, "units": units, "flights": flights,
        "too_heavy": too_heavy, "flight_min": flight_min, "oneway_min": oneway_min,
        "netto": netto, "brutto": brutto, "drone": drone, "heli": heli, "carry": carry,
        "rotations": rotations, "trips": trips,
        "has_dg": any(i["dg"] for i in items),
    }


# ---------------------------------------------------------------------------
# Layout-Bausteine
# ---------------------------------------------------------------------------
def header(nr: int, title: str, kicker: str):
    st.markdown(
        f"""<div class="lp-header"><div class="lp-title"><span>0{nr}</span> · {title}</div>
        <div class="lp-tag">LIFT PLANNER</div></div>
        <div class="lp-kicker">{kicker}</div>""",
        unsafe_allow_html=True,
    )


def kpi(title, value, sub="", orange=False):
    cls = "lp-kpi orange" if orange else "lp-kpi"
    st.markdown(
        f"""<div class="lp-card"><h4>{title}</h4><div class="{cls}">{value}</div>
        <div class="lp-sub">{sub}</div></div>""",
        unsafe_allow_html=True,
    )


def dg_warning():
    st.markdown(
        """<div class="lp-warn"><b>Gefahrgut an Bord.</b> Akkus und Kraftstoff gelten als Fracht
        als Gefahrgut. Flug nur in der Specific-Kategorie mit Betriebsgenehmigung.
        Einstufung im Einzelfall durch die Behörde (z. B. Austro Control) klären.</div>""",
        unsafe_allow_html=True,
    )


def nav_buttons(prev_page=None, next_page=None):
    c1, _, c3 = st.columns([1, 4, 1])
    if prev_page:
        c1.button("← Zurück", on_click=go, args=(prev_page,), width="stretch")
    if next_page:
        c3.button("Weiter →", on_click=go, args=(next_page,), type="primary",
                  width="stretch")


def de(x, nd=0):
    t = f"{x:,.{nd}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_min(m):
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


# ---------------------------------------------------------------------------
# Seitenleiste
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"<h2 style='color:{ORANGE};margin-bottom:0'>Lift Planner</h2>"
                "<div class='lp-sub'>Drohnenlogistik für Steillagen</div>",
                unsafe_allow_html=True)
    st.write("")
    st.radio("Navigation", PAGES, key="page",
             format_func=lambda p: f"{ICONS[p]}  {p}", label_visibility="collapsed")

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

R = compute()
page = S.page

# ---------------------------------------------------------------------------
# 01 Auftrag
# ---------------------------------------------------------------------------
if page == "Auftrag":
    header(1, "Neuer Auftrag", "Einsatzort und Rahmendaten festlegen")
    left, right = st.columns([3, 2], gap="large")
    with left:
        mid_lat = (S.w_start_lat + S.w_ziel_lat) / 2
        mid_lon = (S.w_start_lon + S.w_ziel_lon) / 2
        pts = [
            {"pos": [S.w_start_lon, S.w_start_lat], "name": f"{S.w_start_name} · {S.w_start_alt} m"},
            {"pos": [S.w_ziel_lon, S.w_ziel_lat], "name": f"{S.w_einsatz} · {S.w_ziel_alt} m"},
        ]
        deck = pdk.Deck(
            map_style="light",
            initial_view_state=pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=13.5, pitch=40),
            layers=[
                pdk.Layer("LineLayer", data=[{"s": pts[0]["pos"], "t": pts[1]["pos"]}],
                          get_source_position="s", get_target_position="t",
                          get_color=[255, 102, 0], get_width=5),
                pdk.Layer("ScatterplotLayer", data=pts, get_position="pos",
                          get_fill_color=[255, 102, 0], get_line_color=[255, 255, 255],
                          stroked=True, line_width_min_pixels=2, get_radius=35, pickable=True),
            ],
            tooltip={"text": "{name}"},
        )
        st.pydeck_chart(deck, width="stretch")
    with right:
        st.text_input("Einsatzname", key="w_einsatz")
        c1, c2 = st.columns(2)
        c1.number_input("Einsatzdauer (h)", 1, 24, key="w_dauer")
        c2.number_input("Teamgröße (Personen)", 1, 20, key="w_team")
        c1, c2, c3 = st.columns(3)
        c1.metric("Strecke", f"{de(R['dist_m'] / 1000, 1)} km")
        c2.metric("Höhendifferenz", f"{R['dh']:.0f} m")
        c3.metric("Steigung", f"{(R['dh'] / R['dist_m'] * 100) if R['dist_m'] else 0:.0f} %")

    with st.expander("Koordinaten und Höhen bearbeiten", expanded=False):
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

    st.markdown(
        f"""<div class="lp-banner"><b>STIHL liefert Geräte und Boxen.</b>
        Drohne, Pilot und Genehmigung kommen vom Partner. Planungswert Nutzlast:
        <b>{S.w_payload:g} kg</b> je Flug.</div>""",
        unsafe_allow_html=True,
    )
    st.write("")
    nav_buttons(next_page="Ausrüstung")

# ---------------------------------------------------------------------------
# 02 Ausrüstung
# ---------------------------------------------------------------------------
elif page == "Ausrüstung":
    header(2, "Ausrüstung", "Geräte und Energieversorgung für den Einsatz wählen")
    cols = st.columns(4)
    for n, e in enumerate(EQUIPMENT):
        with cols[n % 4]:
            with st.container(border=True):
                st.markdown(f"<h4 style='color:{ORANGE};margin:0;padding:0;font-size:1rem'>{e['name']}</h4>"
                            f"<div class='lp-sub'>{de(e['kg'], 1)} kg je Stück</div>",
                            unsafe_allow_html=True)
                st.number_input("Anzahl", 0, 20, key=f"w_q_{e['id']}",
                                label_visibility="collapsed")
    st.write("")
    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.container(border=True):
            st.markdown(f"<h4 style='color:{ORANGE};margin:0;padding:0;font-size:1rem'>Energieversorgung</h4>",
                        unsafe_allow_html=True)
            st.radio("Energie", ["Akku-Lösung", "Benzin-Lösung", "Beides"], key="w_energie",
                     horizontal=True, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            if S.w_energie in ("Akku-Lösung", "Beides"):
                c1.number_input("Anzahl Akkus (je 1,6 kg)", 0, 40, key="w_akkus")
            if S.w_energie in ("Benzin-Lösung", "Beides"):
                c2.number_input("Kraftstoff (Liter)", 0.0, 50.0, step=0.5, key="w_liter")
        if R["has_dg"]:
            dg_warning()
    with right:
        kpi("Gesamtgewicht Ausrüstung", f"{de(R['netto'], 1)} kg", "ohne Transportboxen", orange=True)
    st.write("")
    nav_buttons(prev_page="Auftrag", next_page="Flugplan")

# ---------------------------------------------------------------------------
# 03 Flugplan
# ---------------------------------------------------------------------------
elif page == "Flugplan":
    header(3, "Flugplan", "Automatisch optimierte Verteilung der Lasten auf mehrere Flüge")
    if R["too_heavy"]:
        names = ", ".join(u["label"] for u in R["too_heavy"])
        st.error(f"Zu schwer für die Drohne ({S.w_payload:g} kg): {names}. "
                 "Nutzlast erhöhen oder Last aufteilen.")
    if R["has_dg"]:
        dg_warning()

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Flüge")
        if not R["flights"]:
            st.info("Keine Ausrüstung gewählt.")
        for n, f in enumerate(R["flights"], 1):
            pct = min(f["load"] / S.w_payload * 100, 100)
            labels = " · ".join(u["label"] for u in f["units"])
            dg = " · ⚠️ Gefahrgut" if any(u["dg"] for u in f["units"]) else ""
            st.markdown(
                f"""<div class="lp-flight"><b style="color:{ORANGE}">Flug {n}</b> · {de(f['load'], 1)} kg{dg}
                <div class="lp-bar"><div style="width:{pct:.0f}%"></div></div>
                <span class="lp-sub">{labels} · ≈ {fmt_min(R['flight_min'])} ·
                {de(R['dist_m'] / 1000, 2)} km / +{R['dh']:.0f} m</span></div>""",
                unsafe_allow_html=True,
            )

        st.markdown("#### Packliste")
        rows = []
        for u in R["units"]:
            for i in u["items"]:
                rows.append({"Einheit": u["label"], "Inhalt": i["name"], "Gewicht (kg)": i["kg"],
                             "Gefahrgut": "ja" if i["dg"] else ""})
        pack_df = pd.DataFrame(rows)
        if not pack_df.empty:
            summary = pd.DataFrame([{"Einheit": u["label"], "Netto (kg)": round(u["netto"], 1),
                                     "Brutto (kg)": round(u["brutto"], 1),
                                     "Inhalt": ", ".join(i["name"] for i in u["items"])}
                                    for u in R["units"]])
            st.dataframe(summary, hide_index=True, width="stretch")
            st.download_button("Packliste exportieren (CSV)",
                               pack_df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name="packliste.csv", mime="text/csv")
    with right:
        c1, c2 = st.columns(2)
        with c1:
            kpi("Flüge", f"{len(R['flights'])}", f"Nutzlast {S.w_payload:g} kg", orange=True)
        with c2:
            kpi("Gesamtgewicht", f"{de(R['brutto'])} kg", "inkl. Boxen")
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            kpi("Gesamtzeit", fmt_min(len(R["flights"]) * R["flight_min"]), "alle Flüge inkl. Handling")
        with c2:
            kpi("Strecke je Flug", f"{de(R['dist_m'] / 1000, 2)} km", f"Höhendifferenz +{R['dh']:.0f} m")
    st.write("")
    nav_buttons(prev_page="Ausrüstung", next_page="Einsparungen")

# ---------------------------------------------------------------------------
# 04 Einsparungen
# ---------------------------------------------------------------------------
elif page == "Einsparungen":
    header(4, "Einsparungen", "Vergleich von Zeit, Kosten und CO₂ für diesen Einsatz")
    d, h, c = R["drone"], R["heli"], R["carry"]
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Drohne", f"{len(R['flights'])} Flüge",
            f"{fmt_min(d['Zeit (min)'])} · {de(d['Kosten (€)'])} € · {de(d['CO₂ (kg)'], 1)} kg CO₂",
            orange=True)
    with c2:
        kpi("Helikopter", f"{R['rotations']} Rotation{'en' if R['rotations'] != 1 else ''}",
            f"{fmt_min(h['Zeit (min)'])} · {de(h['Kosten (€)'])} € · {de(h['CO₂ (kg)'])} kg CO₂")
    with c3:
        kpi("Tragen", f"{R['trips']} Gang{'e' if R['trips'] != 1 else ''}",
            f"{fmt_min(c['Zeit (min)'])} · {de(c['Kosten (€)'])} € · {S.w_team} Personen")

    df = pd.DataFrame([
        {"Variante": "Drohne", **d}, {"Variante": "Helikopter", **h}, {"Variante": "Tragen", **c},
    ])
    color = alt.Scale(domain=["Drohne", "Helikopter", "Tragen"], range=[ORANGE, GREY_MID, "#4A4A4A"])
    st.write("")
    cols = st.columns(3)
    for col, metric in zip(cols, ["Kosten (€)", "Zeit (min)", "CO₂ (kg)"]):
        with col:
            st.markdown(f"**{metric.replace(' (', ' · ').rstrip(')')}**")
            chart = (
                alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(x=alt.X("Variante:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y(f"{metric}:Q", title=None),
                        color=alt.Color("Variante:N", scale=color, legend=None),
                        tooltip=["Variante", alt.Tooltip(f"{metric}:Q", format=",.1f")])
                .properties(height=240)
            )
            st.altair_chart(chart, width="stretch")

    save_eur = h["Kosten (€)"] - d["Kosten (€)"]
    save_co2 = h["CO₂ (kg)"] - d["CO₂ (kg)"]
    save_h = (c["Zeit (min)"] - d["Zeit (min)"]) / 60
    if R["flights"]:
        st.markdown(
            f"""<div class="lp-banner">Gegenüber Helikopter: <b>{de(save_eur)} € und
            {de(save_co2)} kg CO₂</b> Differenz. Gegenüber Tragen: <b>{de(save_h, 1)} h</b>
            Zeitdifferenz für das Team.</div>""",
            unsafe_allow_html=True,
        )
    if R["has_dg"]:
        dg_warning()
    st.write("")
    nav_buttons(prev_page="Flugplan")

st.markdown(
    "<div class='lp-footer'>Konzeptprototyp · TH Köln × STIHL · Projekt Arbeiten in Steillagen · "
    "Alle Werte sind Beispielwerte und ersetzen keine Flugplanung oder behördliche Genehmigung.</div>",
    unsafe_allow_html=True,
)
