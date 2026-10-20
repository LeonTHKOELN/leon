"""Schritt 4 · Wirtschaftlichkeit: Drohne, Helikopter und Tragen im Vergleich."""
import pandas as pd
import streamlit as st

from core.fmt import de, fmt_min
from ui import charts, state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title

PATH = "views/wirtschaftlichkeit.py"
R = state.result()
d, h, c, j = R["drohne"], R["heli"], R["manuell"], R["job"]

page_head(PATH, "Wirtschaftlichkeit", "Drohne im Vergleich zu Helikopter und Tragen für diesen Einsatz.")
if R["usecase"] == "Heuernte":
    note("Verglichen werden die <b>Transportkosten</b>. Mähen, Zusammenblasen und Befüllen sind bei allen Verfahren "
         "gleich und nicht enthalten. Beim Helikopter trägt das Team die Geräte, der Heli fliegt nur das Heu.")
    st.write("")
if d["fluege"]:
    st.markdown(
        f"""<div class="lp-hero">
          <div><div class="t">Gegenüber Helikopter</div><div class="big">{de(h['Kosten (€)'] - d['Kosten (€)'])} €</div>
            <div class="sub">Kostendifferenz für diesen Einsatz</div></div><div class="div"></div>
          <div><div class="t">CO₂</div><div class="big">{de(h['CO₂ (kg)'] - d['CO₂ (kg)'])} kg</div>
            <div class="sub">Differenz zum Helikopter</div></div><div class="div"></div>
          <div><div class="t">Gegenüber Tragen</div><div class="big">{de((c['Zeit (min)'] - d['Zeit (min)']) / 60, 1)} h</div>
            <div class="sub">weniger Zeit vor Ort als beim Tragen</div></div>
        </div>""", unsafe_allow_html=True)
st.write("")
kpis([kpi_html("Drohne", str(d["fluege"]), " Flüge",
               f"{fmt_min(d['Zeit (min)'])} · {de(d['Kosten (€)'])} € · {de(d['CO₂ (kg)'], 1)} kg CO₂", accent=True),
      kpi_html("Helikopter", str(h["einsaetze"]), " Einsätze",
               f"{fmt_min(h['Zeit (min)'])} · {de(h['Kosten (€)'])} € · {de(h['CO₂ (kg)'])} kg CO₂"),
      kpi_html("Tragen", str(c["gaenge"]), " Gänge",
               f"{fmt_min(c['Zeit (min)'])} · {de(c['Kosten (€)'])} € · {j['team']} Personen")])
st.write("")
df = pd.DataFrame([{"Variante": "Drohne", **{k: d[k] for k in ("Kosten (€)", "Zeit (min)", "CO₂ (kg)")}},
                   {"Variante": "Helikopter", **{k: h[k] for k in ("Kosten (€)", "Zeit (min)", "CO₂ (kg)")}},
                   {"Variante": "Tragen", **{k: c[k] for k in ("Kosten (€)", "Zeit (min)", "CO₂ (kg)")}}])
cols = st.columns(3, gap="medium")
for col, (metric, label, nd) in zip(cols, [("Kosten (€)", "Kosten in €", 0), ("Zeit (min)", "Zeit vor Ort in Minuten", 0),
                                           ("CO₂ (kg)", "CO₂ in kg", 1)]):
    with col, st.container(border=True):
        section_title(label)
        st.altair_chart(charts.compare_chart(df, metric, nd), width="stretch")
st.write("")
section_title("Kostenaufschlüsselung Drohne")
with st.container(border=True):
    if d["positionen"]:
        modell = "Dienstleister" if R["p"]["modell.dienstleister"] else (
            "Eigenbetrieb autonom" if R["p"]["modell.autonom"] else "Eigenbetrieb")
        kpis([kpi_html("Fixe Kosten", de(d["fix"]), "€", "Anreise, Aufbau/Abbau, Wartezeit, Tagessätze"),
              kpi_html("Variable Kosten", de(d["variabel"]), "€", "abhängig von Flugzeit und Flügen"),
              kpi_html("Modell", modell, "", f"{d['tage']} Einsatztag(e) · {d['anfahrten']} Anfahrt(en)")])
        st.caption(d["variante"])
        st.write("")
        pos = pd.DataFrame(d["positionen"])
        pos["Betrag €"] = pos["Betrag"].round(0)
        st.dataframe(pos[["Einsatztag", "Position", "Gruppe", "Art", "Eingesetzt", "Betrag €"]], hide_index=True,
                     width="stretch")
        st.caption(f"Anbieter: {R['anreise']['anbieter']['name']} · Anreise {de(R['anreise']['km'], 1)} km · "
                   f"Heli-Basis: {R['heli_basis']['anbieter']['name']} · {h['einsaetze']} Heli-Einsatz/Einsätze")
    else:
        note("Keine Flüge geplant.")

st.write("")
note("Alle Werte beruhen auf Annahmen. Wie jede Zahl entsteht, zeigt der Rechenweg unter "
     "<b>Annahmen & Parameter</b>. Dort lassen sich alle Werte ändern und als Szenario speichern.")
st.page_link("views/parameter.py", label="Zu Annahmen & Parameter", icon=":material/tune:")
if R["has_dg"]:
    st.write("")
    dg_note()
nav(PATH)
footer()
