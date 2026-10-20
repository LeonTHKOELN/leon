"""Schritt 5 · Flugplan: Boxen, Flüge je Einsatztag, Heuflüge, Packliste."""
import pandas as pd
import streamlit as st

from core.fmt import de, fmt_min
from ui import state
from ui.components import dg_note, footer, kpi_html, kpis, nav, note, page_head, section_title

PATH = "views/flugplan.py"
R = state.result()
p, P, d, H = R["p"], R["P"], R["drohne"], R["heu"]
cap = p["drohne.nutzlast_kg"]
HEU = R["usecase"] == "Heuernte" and H and H["ok"]


def flug_karte(titel, load, chips, meta, dg=False):
    pct = min(load / cap * 100, 100)
    tag = ' · <span style="color:#E05A00;font-weight:700">Gefahrgut</span>' if dg else ""
    st.markdown(
        f"""<div class="lp-flight"><div class="hd"><div class="no">{titel}</div>
        <div class="kg">{de(load, 1)} kg <small>/ {de(cap)} kg</small></div></div>
        <div class="lp-bar"><div style="width:{pct:.0f}%"></div></div>{chips}
        <div class="lp-meta">{meta}{tag}</div></div>""", unsafe_allow_html=True)


page_head(PATH, "Flugplan", "Lasten werden automatisch in Boxen gepackt und auf Flüge verteilt.")
if R["too_heavy"]:
    names = ", ".join(u["label"] for u in R["too_heavy"])
    note(f"<b>Zu schwer für die Drohne ({de(cap)} kg):</b> {names}. Nutzlast unter Annahmen & Parameter "
         "erhöhen oder Last aufteilen.", warn=True, icon="!")
    st.write("")
kpis([kpi_html("Flüge gesamt", str(d["fluege"]), "", f"Nutzlast {de(cap)} kg · alle Einsatztage", accent=True),
      kpi_html("Zeit je Umlauf", de(d["umlauf_min"], 1), "min", f"{de(P['flight_len'] / 1000, 2)} km je Richtung"),
      kpi_html("Zeit vor Ort", fmt_min(d["Zeit (min)"]), "", "inkl. Aufbau und Abbau")])
st.write("")

left, right = st.columns([6, 6], gap="large")
with left:
    for name, pk in R["packs"]:
        section_title(f"{name} · Geräte hoch und abends runter" if (HEU or R["job"]["rueck"]) else f"{name} · Geräte hoch")
        if not pk["flights"]:
            note("Noch keine Ausrüstung gewählt.")
        for n, f in enumerate(pk["flights"], 1):
            chips = "".join(f'<span class="lp-chip {"o" if u["dg"] else ""}">{u["label"]}</span>' for u in f["units"])
            flug_karte(f"<span>Flug</span> {n}", f["load"], chips,
                       f"≈ {fmt_min(d['umlauf_min'])} je Umlauf · beladen bergauf",
                       dg=any(u["dg"] for u in f["units"]))
        st.write("")
    if HEU:
        section_title("Erntetag · Heu ins Tal")
        chips = f'<span class="lp-chip o">{H["je_flug"]} × Heusammelsack</span>'
        flug_karte(f"<span>{H['fluege']} ×</span> Heuflug", H["last"], chips,
                   f"{de(H['je_sack'], 1)} kg Heu je Sack · beladen bergab, leer bergauf · "
                   f"{fmt_min(H['flug_h'] * 60)} gesamt")
    if R["has_dg"]:
        dg_note()
with right:
    section_title("Packliste")
    for name, pk in R["packs"]:
        if not pk["units"]:
            continue
        if len(R["packs"]) > 1:
            st.markdown(f"**{name}**")
        summary = pd.DataFrame([{"Einheit": u["label"], "Inhalt": ", ".join(i["name"] for i in u["items"]),
                                 "Netto kg": round(u["netto"], 1), "Brutto kg": round(u["brutto"], 1)}
                                for u in pk["units"]])
        st.dataframe(summary, hide_index=True, width="stretch",
                     column_config={"Inhalt": st.column_config.TextColumn(width="large")})
    rows = [{"Einsatztag": name, "Einheit": u["label"], "Inhalt": i["name"], "Gewicht (kg)": round(i["kg"], 2),
             "Gefahrgut": "ja" if i["dg"] else ""} for name, pk in R["packs"] for u in pk["units"] for i in u["items"]]
    if rows:
        st.download_button("Packliste exportieren (CSV)",
                           pd.DataFrame(rows).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name="packliste.csv", mime="text/csv", width="stretch")
nav(PATH, next_label="Vergleich")
footer()
