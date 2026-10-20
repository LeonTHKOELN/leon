"""Schritt 2 · Anbieter & Anreise: nächster Dienstleister, Anreise, Heli-Basis, Betriebsmodell."""
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from core.fmt import de, fmt_min
from ui import state
from ui.components import footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import GREY_600, INK, ORANGE

PATH = "views/anbieter.py"
S = state.S


def set_modell():
    S["p.modell.dienstleister"] = S.sel_modell == "Dienstleister"
    S.szenario = "Eigene Werte"


def set_autonom():
    S["p.modell.autonom"] = bool(S.sel_autonom)
    S.szenario = "Eigene Werte"


R = state.result()
p, j, d, h = R["p"], R["job"], R["drohne"], R["heli"]
opts, an, hb = R["optionen"], R["anreise"], R["heli_basis"]

page_head(PATH, "Anbieter & Anreise", "Nächsten Drohnen-Dienstleister wählen und die Anreise berechnen.")

left, right = st.columns([7, 5], gap="large")
with left:
    start, ziel = j["start"], j["ziel"]
    m = folium.Map(location=start, zoom_start=11, tiles=None, control_scale=True)
    folium.TileLayer(tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                     attr='Karte: © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA), '
                          '© OpenStreetMap-Mitwirkende · Routing: OSRM', max_zoom=17).add_to(m)
    bounds = [start, ziel]
    if an.get("geometry"):
        folium.PolyLine(an["geometry"], color=ORANGE, weight=5, opacity=.9).add_to(m)
        bounds += [an["geometry"][0]]
    if hb["anbieter"].get("lat") is not None:
        hpos = (hb["anbieter"]["lat"], hb["anbieter"]["lon"])
        folium.PolyLine([hpos, start], color=INK, weight=2, opacity=.6, dash_array="6 6").add_to(m)
        bounds += [hpos]
    for o in opts:
        a = o["anbieter"]
        sel = a["id"] == an["anbieter"]["id"]
        folium.CircleMarker((a["lat"], a["lon"]), radius=9 if sel else 6, color=ORANGE, weight=3, fill=True,
                            fill_color=ORANGE if sel else "#FFFFFF", fill_opacity=1,
                            tooltip=f"{a['name']}{' (fiktiv)' if a['fiktiv'] else ''}").add_to(m)
    for b in R["heli_basen"]:
        a = b["anbieter"]
        folium.CircleMarker((a["lat"], a["lon"]), radius=8, color="#FFFFFF", weight=2, fill=True,
                            fill_color=INK, fill_opacity=1, tooltip=f"Heli-Basis {a['name']}").add_to(m)
    folium.CircleMarker(start, radius=8, color=ORANGE, weight=4, fill=True, fill_color="#FFFFFF", fill_opacity=1,
                        tooltip=f"Landeplatz · {S.w_start_name}").add_to(m)
    m.fit_bounds(bounds, padding=(40, 40))
    st_folium(m, height=420, width="100%", returned_objects=[], key="map_anbieter")
    st.caption("Orange: Drohnen-Anbieter und Anfahrt über die Straße · Schwarz gestrichelt: Heli-Basis und "
               "Anflug in Luftlinie · Ring: Landeplatz")

with right:
    with st.container(border=True):
        section_title("Betriebsmodell")
        S.sel_modell = "Dienstleister" if p["modell.dienstleister"] else "Eigenbetrieb"
        st.segmented_control("Modell", ["Dienstleister", "Eigenbetrieb"], key="sel_modell", on_change=set_modell,
                             label_visibility="collapsed")
        if not p["modell.dienstleister"]:
            S.sel_autonom = bool(p["modell.autonom"])
            st.toggle("Autonomer Flugbetrieb (hypothetisch)", key="sel_autonom", on_change=set_autonom,
                      help="Pilot entfällt. Fernüberwachung und Bodenpersonal werden weiter berechnet.")
        st.caption("Dienstleister: Stundensatz inkl. Pilot und Drohne. Eigenbetrieb: alle Kosten einzeln. "
                   "Sätze unter Annahmen & Parameter.")
    st.write("")
    kpis([kpi_html("Anreise", de(an["km"], 1), "km", "einfache Strecke"),
          kpi_html("Fahrzeit", de(an["route_min"] + p["anreise.zuschlag_min"]), "min",
                   f"inkl. {de(p['anreise.zuschlag_min'])} min letzte Meile"),
          kpi_html("Anfahrten", str(d.get("anfahrten", 0) * d.get("tage", 1)), "",
                   d.get("variante", ""))])
    st.write("")
    anreise_eur = sum(x["Betrag"] for x in d.get("positionen", []) if x["Gruppe"] == "Anreise")
    kpis([kpi_html("Anreisekosten", de(anreise_eur), "€", "Fahrzeug und Personal, alle Anfahrten", accent=True),
          kpi_html("Heli-Anflug", de(h.get("anflug_min", 0)), "min",
                   f"hin und zurück · {de(hb['km'], 1)} km Luftlinie, der Heli fliegt direkt")],
         two=True)

st.write("")
section_title("Drohnen-Anbieter nach Fahrzeit")
if not opts:
    note("Keine Drohnen-Anbieter hinterlegt. Unter Einstellungen › Anbieter einen Anbieter anlegen.", warn=True,
         icon="!")
else:
    ids = [o["anbieter"]["id"] for o in opts]
    df = pd.DataFrame([{
        "Anbieter": o["anbieter"]["name"] + (" · fiktiv" if o["anbieter"]["fiktiv"] else ""),
        "Ort": o["anbieter"]["adresse"],
        "Straße km": round(o["km"], 1),
        "Fahrzeit min": round(o["route_min"] + p["anreise.zuschlag_min"]),
        "Berechnung": o["quelle"],
    } for o in opts])
    st.dataframe(df, hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    S.w_anbieter = an["anbieter"]["id"] if S.w_anbieter not in ids else S.w_anbieter
    c1.selectbox("Gewählter Drohnen-Anbieter", ids, key="w_anbieter",
                 format_func=lambda i: next(o["anbieter"]["name"] for o in opts if o["anbieter"]["id"] == i),
                 help="Vorausgewählt ist der Anbieter mit der kürzesten Fahrzeit.")
    basen = R["heli_basen"]
    if basen:
        bids = [b["anbieter"]["id"] for b in basen]
        S.w_heli_basis = hb["anbieter"]["id"] if S.w_heli_basis not in bids else S.w_heli_basis
        c2.selectbox("Helikopter-Basis", bids, key="w_heli_basis",
                     format_func=lambda i: next(f"{b['anbieter']['name']} · {de(b['km'], 1)} km"
                                                for b in basen if b["anbieter"]["id"] == i))
    if an.get("snap_m", 0) > 100:
        note(f"Der Landeplatz liegt rund <b>{de(an['snap_m'])} m</b> von der nächsten befahrbaren Straße entfernt. "
             f"Diese letzte Strecke deckt der Zuschlag letzte Meile ({de(p['anreise.zuschlag_min'])} min) ab.",
             icon="i")
    if 0 < an["km"] < 1:
        note("Anbieter und Landeplatz liegen praktisch am selben Ort, die Anreise fällt kaum ins Gewicht.", icon="i")
    if an["anbieter"].get("fiktiv"):
        note(f"<b>{an['anbieter']['name']}</b> ist ein fiktiver Anbieter für die Konzeptdarstellung.")
    if hb["anbieter"].get("koord_quelle", "").startswith("ungefähr"):
        note("Die Adresse der Heli-Basis konnte nicht nachgeschlagen werden. Es wird ein ungefährer Standort "
             "verwendet.", warn=True, icon="!")
    if any(o["quelle"].startswith("Ersatz") for o in opts[:1]):
        note("Straßenrouting nicht erreichbar. Strecke und Fahrzeit sind aus Luftlinie × Umwegfaktor geschätzt.",
             warn=True, icon="!")
nav(PATH)
footer()
