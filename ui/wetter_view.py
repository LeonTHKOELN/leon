"""Anzeige der Wettervorhersage mit Flug-Ampel und Erntefenster."""
import html

import pandas as pd
import streamlit as st

from core import wetter
from core.fmt import de
from ui import state
from ui.components import note, section_title
from ui.theme import GREY_600

FARBE = {"grün": "#2F7A3E", "gelb": "#E0A100", "rot": "#C62828"}


def _f(v, nd=0, einheit=""):
    return "–" if v is None else f"{de(v, nd)}{einheit}"


def anzeigen(R):
    p, P = R["p"], R["P"]
    section_title("Wetter am Einsatzort")
    tage, fehler = state.wetter_laden(R["job"]["ziel"], P["ziel_alt"])
    if not tage:
        note("Wettervorhersage derzeit nicht erreichbar. Später erneut laden.", warn=True, icon="!")
        return

    fenster = []
    if R["usecase"] == "Heuernte":
        fenster = wetter.erntefenster(tage, p, p["heu.trocknung_tage"])
    markiert = set()
    if fenster:
        f = fenster[0]
        markiert = {f["maehtag"]["datum"], f["erntetag"]["datum"]}

    karten = []
    for t in tage[:14]:
        ampel, gruende = wetter.flugampel(t, p)
        sym, txt = wetter.WMO.get(t["code"], ("·", ""))
        tip = html.escape(f"{txt}. " + ("; ".join(gruende) if gruende else "flugtauglich"))
        karten.append(
            f'<div class="lp-wx-day {ampel} {"sel" if t["datum"] in markiert else ""}" title="{tip}">'
            f'<div class="d">{wetter.tagname(t["datum"])}</div><div class="i">{sym}</div>'
            f'<div class="t">{_f(t["tmax"])}° / {_f(t["tmin"])}°</div>'
            f'<div class="m">💧 {_f(t["regen_mm"], 1)} mm · {_f(t["regen_pct"])} %</div>'
            f'<div class="m">💨 Böen {_f(t["boe"])} m/s</div>'
            f'<div class="m">↑ Höhe {_f(t["wind_hoehe"])} m/s</div>'
            f'<div class="m">☀ {_f(t["sonne_h"], 1)} h</div></div>')
    st.markdown(f'<div class="lp-wx">{"".join(karten)}</div>', unsafe_allow_html=True)
    st.markdown(
        f"<div class='lp-wx-legend' style='color:{GREY_600};font-size:.8rem;margin-top:6px'>Flug-Ampel:"
        + "".join(f"<span style='background:{c}'></span>{n}" for n, c in FARBE.items())
        + f" · Grenzen: Wind {de(p['wetter.wind_max_ms'])} m/s, Böen {de(p['wetter.boe_max_ms'])} m/s, "
          f"Regen {de(p['wetter.regen_max_mm'], 1)} mm, ab {de(p['wetter.temp_min_c'])} °C · "
          "Mauszeiger auf einen Tag zeigt die Gründe</div>", unsafe_allow_html=True)

    if R["usecase"] == "Heuernte":
        st.write("")
        t_tr = int(p["heu.trocknung_tage"])
        if fenster:
            f = fenster[0]
            tr = ", ".join(wetter.tagname(x["datum"]) for x in f["trocknung"]) or "keine"
            note(f"<b>Vorgeschlagenes Erntefenster:</b> Mähen <b>{wetter.tagname(f['maehtag']['datum'])}</b> · "
                 f"Trocknung {tr} · Ernte <b>{wetter.tagname(f['erntetag']['datum'])}</b><br>"
                 f"Flugtage {f['ampel'][0]} / {f['ampel'][1]} · {de(f['sonne_h'], 1)} Sonnenstunden zum Trocknen",
                 icon="✓")
            if len(fenster) > 1:
                alt = " · ".join(f"{wetter.tagname(x['maehtag']['datum'])} → {wetter.tagname(x['erntetag']['datum'])}"
                                 for x in fenster[1:])
                st.caption(f"Alternativen: {alt}")
        else:
            note(f"In den nächsten {len(tage)} Tagen gibt es kein Erntefenster mit flugtauglichem Mäh- und Erntetag "
                 f"und {t_tr} trockenem Tag dazwischen. Grenzwerte unter Annahmen & Parameter › Wetter.",
                 warn=True, icon="!")

    with st.expander(f"Alle {len(tage)} Tage als Tabelle"):
        rows = []
        for t in tage:
            ampel, gruende = wetter.flugampel(t, p)
            rows.append({"Tag": wetter.tagname(t["datum"]), "Wetter": wetter.WMO.get(t["code"], ("", ""))[1],
                         "Ampel": ampel, "Max °C": t["tmax"], "Min °C": t["tmin"], "Regen mm": t["regen_mm"],
                         "Regen %": t["regen_pct"], "Böen m/s": t["boe"], "Wind Höhe m/s": t["wind_hoehe"],
                         "Sonne h": round(t["sonne_h"], 1) if t["sonne_h"] is not None else None,
                         "Trocknung": "ja" if wetter.trocken(t, p) else "", "Gründe": "; ".join(gruende)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Vorhersage: Open-Meteo (CC BY 4.0) für Lage und Höhe des Einsatzorts. Im Gebirge sind Talwinde "
               "und Gewitter schwer vorherzusagen, ab etwa 5 bis 7 Tagen nimmt die Genauigkeit deutlich ab. "
               "Planungshilfe, die Entscheidung trifft der Pilot vor Ort.")
