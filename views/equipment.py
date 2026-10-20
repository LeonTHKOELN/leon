"""Schritt 3 · Equipment: Geräte, Material und Energieversorgung."""
import streamlit as st

from core.fmt import de
from core.packen import ENERGIE_OPTIONEN
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import GREY_600

PATH = "views/equipment.py"
S = state.S
R = state.result()
p = R["p"]
HEU = R["usecase"] == "Heuernte"


def geraete_heu():
    section_title("Geräte je Einsatztag")
    st.caption("Bei der Heuernte ergibt sich die Ausrüstung aus der Teamgröße und der Anzahl Säcke.")
    for col, (name, pkx) in zip(st.columns(2), R["packs"]):
        with col, st.container(border=True):
            st.markdown(f"<div class='lp-eq-name'>{name}</div>", unsafe_allow_html=True)
            zaehler = {}
            for it in pkx["items"]:
                zaehler[it["name"]] = zaehler.get(it["name"], 0) + 1
            st.markdown("".join(f'<span class="lp-chip {"o" if "Akku" in n or "Kraftstoff" in n else ""}">'
                                f'{k} × {n}</span>' for n, k in zaehler.items()), unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px;color:{GREY_600};font-size:.85rem'>{de(pkx['netto'], 1)} kg "
                        "netto · morgens hoch, abends runter</div>", unsafe_allow_html=True)
    st.caption("Gewichte unter Annahmen & Parameter › Geräte und Material, Säcke unter › Heusammelsack.")


def geraete_forst():
    section_title("Geräte und Material")
    ids = list(state.GERAETE)
    for row in [ids[i:i + 4] for i in range(0, len(ids), 4)]:
        for col, gid in zip(st.columns(4), row):
            meta = S[f"m.geraet.{gid}"]
            with col, st.container(border=True):
                chip = "lp-chip o" if S.get(f"w_q_{gid}", 0) else "lp-chip"
                st.markdown(f'<div class="lp-eq-name">{state.GERAETE[gid]}<br>'
                            f'<span style="color:{GREY_600};font-weight:500;font-size:.82rem">{meta["kommentar"]}'
                            f'</span></div><span class="{chip}">{de(p[f"geraet.{gid}"], 1)} kg</span>',
                            unsafe_allow_html=True)
                st.number_input("Anzahl", 0, 20, key=f"w_q_{gid}", label_visibility="collapsed")
    st.caption("Gewichte je Stück unter Annahmen & Parameter › Geräte und Material.")


page_head(PATH, "Equipment", "Geräte und Energieversorgung für den Einsatz wählen.")
left, right = st.columns([8, 4], gap="large")
with left:
    if HEU:
        geraete_heu()
    else:
        geraete_forst()
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
    alle = [i for _, pkx in R["packs"] for i in pkx["items"]]
    n_items = sum(1 for i in alle if not i["dg"])
    dg_kg = max(sum(i["kg"] for i in pkx["items"] if i["dg"]) for _, pkx in R["packs"])
    netto = max(pkx["netto"] for _, pkx in R["packs"])
    st.markdown(kpi_html("Gesamtgewicht", de(netto, 1), "kg",
                         "größter Einsatztag, ohne Boxen" if HEU else "ohne Transportboxen", accent=True),
                unsafe_allow_html=True)
    st.write("")
    kpis([kpi_html("Teile", str(n_items), "", "Geräte und Material" + (", alle Tage" if HEU else "")),
          kpi_html("Gefahrgut", de(dg_kg, 1), "kg", "Akkus und Kraftstoff")], two=True)
    st.write("")
    if R["has_dg"]:
        dg_note()
    else:
        note("Kein Gefahrgut an Bord. Flug ohne Gefahrgut-Auflagen planbar.")
nav(PATH)
footer()
