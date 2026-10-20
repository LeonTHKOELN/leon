"""Schritt 3 · Flugplan: Boxen, Flüge, Packliste."""
import pandas as pd
import streamlit as st

from core.fmt import de, fmt_min
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title

PATH = "views/flugplan.py"
R = state.result()
p, pk, P, d = R["p"], R["pack"], R["P"], R["drohne"]
cap = p["drohne.nutzlast_kg"]

page_head(PATH, "Flugplan", "Lasten werden automatisch in Boxen gepackt und auf Flüge verteilt.")
if pk["too_heavy"]:
    names = ", ".join(u["label"] for u in pk["too_heavy"])
    note(f"<b>Zu schwer für die Drohne ({de(cap)} kg):</b> {names}. Nutzlast unter Annahmen & Parameter "
         "erhöhen oder Last aufteilen.", warn=True, icon="!")
    st.write("")
kpis([kpi_html("Flüge", str(len(pk["flights"])), "", f"Nutzlast {de(cap)} kg", accent=True),
      kpi_html("Gesamtgewicht", de(pk["brutto"]), "kg", "inkl. Boxen"),
      kpi_html("Gesamtzeit", fmt_min(d["Zeit (min)"]), "", "inkl. Handling")])
st.write("")
left, right = st.columns([6, 6], gap="large")
with left:
    section_title("Flüge")
    if not pk["flights"]:
        note("Noch keine Ausrüstung gewählt.")
    for n, f in enumerate(pk["flights"], 1):
        pct = min(f["load"] / cap * 100, 100)
        chips = "".join(f'<span class="lp-chip {"o" if u["dg"] else ""}">{u["label"]}</span>' for u in f["units"])
        dg = (' · <span style="color:#E05A00;font-weight:700">Gefahrgut</span>'
              if any(u["dg"] for u in f["units"]) else "")
        st.markdown(
            f"""<div class="lp-flight"><div class="hd"><div class="no"><span>Flug</span> {n}</div>
            <div class="kg">{de(f['load'], 1)} kg <small>/ {de(cap)} kg</small></div></div>
            <div class="lp-bar"><div style="width:{pct:.0f}%"></div></div>{chips}
            <div class="lp-meta">≈ {fmt_min(d['umlauf_min'])} · {de(2 * P['flight_len'] / 1000, 2)} km hin und zurück ·
            {'+' if P['dh'] >= 0 else '−'}{de(abs(P['dh']))} m{dg}</div></div>""", unsafe_allow_html=True)
    if pk["has_dg"]:
        dg_note()
with right:
    section_title("Packliste")
    if pk["units"]:
        summary = pd.DataFrame([{"Einheit": u["label"], "Inhalt": ", ".join(i["name"] for i in u["items"]),
                                 "Netto kg": round(u["netto"], 1), "Brutto kg": round(u["brutto"], 1)}
                                for u in pk["units"]])
        st.dataframe(summary, hide_index=True, width="stretch",
                     column_config={"Inhalt": st.column_config.TextColumn(width="large")})
        rows = [{"Einheit": u["label"], "Inhalt": i["name"], "Gewicht (kg)": round(i["kg"], 2),
                 "Gefahrgut": "ja" if i["dg"] else ""} for u in pk["units"] for i in u["items"]]
        st.download_button("Packliste exportieren (CSV)",
                           pd.DataFrame(rows).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name="packliste.csv", mime="text/csv", width="stretch")
nav(PATH, next_label="Vergleich")
footer()
