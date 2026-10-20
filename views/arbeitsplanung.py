"""Schritt 4 · Arbeitsplanung: Ablauf über die Einsatztage, Arbeitszeiten und Engpass."""
import altair as alt
import pandas as pd
import streamlit as st

from core.fmt import de, fmt_min
from ui import state
from ui.components import footer, kpi_html, kpis, nav, note, page_head, section_title
from ui.theme import FONT, GREY_400, GREY_600, GREY_900, ORANGE

PATH = "views/arbeitsplanung.py"
R = state.result()
p, j, d, H = R["p"], R["job"], R["drohne"], R["heu"]

page_head(PATH, "Arbeitsplanung", "Ablauf über die Einsatztage mit Arbeitszeiten von Team und Drohne.")

if R["usecase"] == "Heuernte" and H and H["ok"]:
    kpis([kpi_html("Heumenge", de(H["heu_kg"]), "kg", f"{de(H['flaeche_ha'], 2)} ha × {de(p['heu.ertrag_kg_ha'])} kg/ha",
                   accent=True),
          kpi_html("Heuflüge", str(H["fluege"]), "",
                   f"{H['je_flug']} Sack je Flug · {de(H['je_sack'], 1)} kg Heu je Sack"),
          kpi_html("Ablauf", str(len(H["ablauf"])), " Tage",
                   f"{H['maeh_tage']} Mähen · {H['trocknung_tage']} Trocknung · {H['ernte_tage']} Ernte")])
    st.write("")
    section_title("Ablauf")
    df = pd.DataFrame(H["ablauf"])
    df["Dauer"] = df["Dauer h"].apply(lambda h: fmt_min(h * 60) if h else "–")
    st.dataframe(df[["Tag", "Phase", "Dauer", "Drohne"]], hide_index=True, width="stretch")

    st.write("")
    section_title("Erntetag im Detail")
    with st.container(border=True):
        blas, fuell, flug = H["blas_h"], H["fuell_h"], H["flug_h"]
        erster = H["je_flug"] * p["sack.befuellzeit_min"] / 60
        if H["parallel"]:
            rows = [("Team", "Zusammenblasen", 0, blas), ("Team", "Säcke befüllen", blas, blas + fuell),
                    ("Drohne", "Heuflüge ins Tal", blas + erster, blas + erster + flug)]
        else:
            rows = [("Team", "Zusammenblasen", 0, blas), ("Team", "Säcke befüllen", blas, blas + fuell),
                    ("Drohne", "Heuflüge ins Tal", blas + fuell, blas + fuell + flug)]
        g = pd.DataFrame(rows, columns=["Wer", "Taetigkeit", "von", "bis"])
        g["Dauer"] = (g["bis"] - g["von"]).apply(lambda h: fmt_min(h * 60))
        chart = alt.Chart(g).mark_bar(cornerRadius=4).encode(
            x=alt.X("von:Q", title="Stunden ab Arbeitsbeginn",
                    axis=alt.Axis(grid=True, gridColor="#F0F0F0",
                                  labelExpr="replace(format(datum.value, '.1f'), '.', ',')")),
            x2="bis:Q",
            y=alt.Y("Taetigkeit:N", sort=None, title=None, scale=alt.Scale(paddingInner=0.35),
                    axis=alt.Axis(labelLimit=220, labelFontSize=13)),
            color=alt.Color("Wer:N", scale=alt.Scale(domain=["Team", "Drohne"], range=[GREY_400, ORANGE]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=["Wer", alt.Tooltip("Taetigkeit:N", title="Tätigkeit"), "Dauer"],
        ).properties(height=alt.Step(44)).configure_view(stroke=None).configure_axis(
            labelFont=FONT, titleFont=FONT, labelColor=GREY_900, titleColor=GREY_600)
        st.altair_chart(chart, width="stretch")
        st.caption(f"Erntezeit gesamt {fmt_min(H['ernte_h'] * 60)} · Arbeitszeit je Tag {j['dauer_h']} h")
    st.write("")
    if H["parallel"]:
        if H["engpass"] == "Drohne":
            note(f"<b>Engpass ist die Drohne.</b> Das Team befüllt schneller ({fmt_min(fuell * 60)}), als die Drohne "
                 f"fliegt ({fmt_min(flug * 60)}). Mehr Nutzlast, kürzere Umläufe oder eine zweite Drohne verkürzen "
                 "den Erntetag.", icon="i")
        else:
            note(f"<b>Engpass ist das Team.</b> Die Drohne wartet auf befüllte Säcke ({fmt_min(fuell * 60)} Befüllen "
                 f"gegenüber {fmt_min(flug * 60)} Flugzeit). Schnelleres Befüllen oder mehr Personen helfen.", icon="i")
    else:
        note(f"<b>Zu wenige Säcke im Umlauf ({int(p['sack.anzahl'])}).</b> Team und Drohne arbeiten nacheinander. "
             "Ab zwei Flugladungen Säcken laufen Befüllen und Fliegen parallel.", warn=True, icon="!")
    if H["ernte_tage"] > 1 or H["maeh_tage"] > 1:
        note(f"Die Arbeit passt nicht in einen Arbeitstag von {j['dauer_h']} h und wird auf mehrere Tage verteilt. "
             "Jeder zusätzliche Tag bedeutet eine weitere Anreise der Drohne.", warn=True, icon="!")
else:
    pk = R["pack"]
    n = len(pk["flights"])
    kpis([kpi_html("Einsatztage", str(j["tage"]), "", "je Tag eine Anreise", accent=True),
          kpi_html("Flüge je Richtung", str(n), "", f"{fmt_min(n * d['umlauf_min'])} Flugzeit"),
          kpi_html("Rücktransport", "ja" if j["rueck"] else "nein", "", d.get("variante", ""))])
    st.write("")
    section_title("Ablauf je Einsatztag")
    rows = [{"Schritt": "Aufbau Drohne", "Wer": "Crew", "Dauer": fmt_min(p["einsatz.aufbau_min"])},
            {"Schritt": "Geräte hoch", "Wer": "Drohne", "Dauer": fmt_min(n * d["umlauf_min"])},
            {"Schritt": "Arbeit am Hang", "Wer": "Team", "Dauer": fmt_min(j["dauer_h"] * 60)}]
    if j["rueck"]:
        rows.append({"Schritt": "Geräte runter", "Wer": "Drohne", "Dauer": fmt_min(n * d["umlauf_min"])})
    rows.append({"Schritt": "Abbau Drohne", "Wer": "Crew", "Dauer": fmt_min(p["einsatz.abbau_min"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if j["rueck"]:
        note(f"Zwischen Hin- und Rücktransport: {d.get('variante', '')}. Die App wählt die günstigere Variante "
             "(warten oder zweite Anfahrt), siehe Rechenweg.", icon="i")
nav(PATH)
footer()
