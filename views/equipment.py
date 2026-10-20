"""Schritt 2 · Equipment: Geräte, Material und Energieversorgung."""
import streamlit as st

from core.fmt import de
from core.packen import ENERGIE_OPTIONEN
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import GREY_600

PATH = "views/equipment.py"
S = state.S
R = state.result()
p, pk = R["p"], R["pack"]

page_head(PATH, "Equipment", "Geräte und Energieversorgung für den Einsatz wählen.")
left, right = st.columns([8, 4], gap="large")
with left:
    section_title("Geräte und Material")
    ids = list(state.GERAETE)
    for row in [ids[i:i + 4] for i in range(0, len(ids), 4)]:
        cols = st.columns(4)
        for col, gid in zip(cols, row):
            meta = S[f"m.geraet.{gid}"]
            with col, st.container(border=True):
                chip = "lp-chip o" if S.get(f"w_q_{gid}", 0) else "lp-chip"
                st.markdown(f'<div class="lp-eq-name">{state.GERAETE[gid]}<br>'
                            f'<span style="color:{GREY_600};font-weight:500;font-size:.82rem">{meta["kommentar"]}</span></div>'
                            f'<span class="{chip}">{de(p[f"geraet.{gid}"], 1)} kg</span>', unsafe_allow_html=True)
                st.number_input("Anzahl", 0, 20, key=f"w_q_{gid}", label_visibility="collapsed")
    st.caption("Gewichte je Stück unter Annahmen & Parameter › Geräte und Material.")
    st.write("")
    section_title("Energieversorgung")
    with st.container(border=True):
        st.radio("Energie", ENERGIE_OPTIONEN, key="w_energie", horizontal=True, label_visibility="collapsed")
        c1, c2 = st.columns(2)
        if S.w_energie in ("Akku-Lösung", "Beides"):
            c1.number_input(f"Anzahl Akkus (je {de(p['akku.gewicht_kg'], 1)} kg)", 0, 40, key="w_akkus")
        if S.w_energie in ("Benzin-Lösung", "Beides"):
            c2.number_input("Kraftstoff (Liter)", 0.0, 50.0, step=0.5, key="w_liter")
with right:
    section_title("Zusammenfassung")
    n_items = sum(1 for i in pk["items"] if not i["dg"])
    dg_kg = sum(i["kg"] for i in pk["items"] if i["dg"])
    st.markdown(kpi_html("Gesamtgewicht", de(pk["netto"], 1), "kg", "ohne Transportboxen", accent=True),
                unsafe_allow_html=True)
    st.write("")
    kpis([kpi_html("Teile", str(n_items), "", "Geräte und Material"),
          kpi_html("Gefahrgut", de(dg_kg, 1), "kg", "Akkus und Kraftstoff")], two=True)
    st.write("")
    if pk["has_dg"]:
        dg_note()
    else:
        note("Kein Gefahrgut an Bord. Flug ohne Gefahrgut-Auflagen planbar.")
nav(PATH)
footer()
