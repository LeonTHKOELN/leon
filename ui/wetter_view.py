"""Anzeige der Wettervorhersage mit Flug-Ampel und Erntefenster."""
import html

import altair as alt
import pandas as pd
import streamlit as st

from core import wetter
from core.fmt import de
from ui import state
from ui.components import note, section_title
from ui.theme import FONT, GREY_600, GREY_900, INK, ORANGE

FARBE = {"grün": "#2F7A3E", "gelb": "#E0A100", "rot": "#C62828"}


def _f(v, nd=0, einheit=""):
    return "–" if v is None else f"{de(v, nd)}{einheit}"


def _karten(tage, p, markiert):
    karten = []
    for t in tage:
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


def _stunden(tage, p, vorauswahl):
    """Stundenansicht eines Tages: Wind, Böen, Regen und flugtaugliche Zeitfenster."""
    mit = [t for t in tage if t.get("stunden")]
    if not mit:
        return
    daten = [t["datum"] for t in mit]
    idx = daten.index(vorauswahl) if vorauswahl in daten else 0
    # Schlüssel enthält die Vorauswahl: ändert sich der vorgeschlagene Tag, springt die Auswahl mit
    tag_id = st.selectbox("Stundenwerte für", daten, index=idx, key=f"wx_tag_{vorauswahl}",
                          format_func=wetter.tagname)
    t = next(x for x in mit if x["datum"] == tag_id)
    std = [h for h in t["stunden"] if 5 <= h["stunde"] <= 21]
    fenster = wetter.flugfenster(t["stunden"], p)
    if fenster:
        txt = " · ".join(f"{a:02d}–{b:02d} Uhr" for a, b in fenster)
        st.markdown(f"**Flugfenster:** {txt}  <span style='color:{GREY_600};font-size:.85rem'>(ohne rote Stunden, "
                    "06–21 Uhr)</span>", unsafe_allow_html=True)
    else:
        st.markdown("**Kein Flugfenster** an diesem Tag zwischen 06 und 21 Uhr.")
    df = pd.DataFrame([{"Uhr": h["stunde"], "Wind in Flughöhe": h["wind_hoehe"], "Böen (10 m)": h["boe"],
                        "Regen mm": h["regen_mm"] or 0, "Temp °C": h["temp"], "Ampel": wetter.stunden_ampel(h, p)}
                       for h in std])
    if df.empty:
        return
    x = alt.X("Uhr:O", title="Uhrzeit", axis=alt.Axis(labelAngle=0, labelExpr="datum.value + ' h'"))
    band = alt.Chart(df).mark_rect(opacity=.12).encode(
        x=x, color=alt.Color("Ampel:N", scale=alt.Scale(domain=list(FARBE), range=list(FARBE.values())), legend=None),
        tooltip=["Uhr", "Ampel"])
    lang = df.melt(id_vars=["Uhr"], value_vars=["Wind in Flughöhe", "Böen (10 m)"], var_name="Größe", value_name="m/s")
    linien = alt.Chart(lang).mark_line(point=True, strokeWidth=2.5).encode(
        x=x, y=alt.Y("m/s:Q", title="m/s"),
        color=alt.Color("Größe:N", scale=alt.Scale(domain=["Wind in Flughöhe", "Böen (10 m)"], range=[ORANGE, INK])),
        tooltip=["Uhr", "Größe", alt.Tooltip("m/s:Q", format=".1f")])
    grenzen = alt.Chart(pd.DataFrame([{"g": p["wetter.wind_max_ms"], "Grenze": "Grenze Wind"},
                                      {"g": p["wetter.boe_max_ms"], "Grenze": "Grenze Böen"}])).mark_rule(
        strokeDash=[5, 4]).encode(y="g:Q", color=alt.value(GREY_600), tooltip=["Grenze", "g"])
    regen = alt.Chart(df).mark_bar(color="#4A7FB0", opacity=.85).encode(
        x=x, y=alt.Y("Regen mm:Q", title="Regen mm"), tooltip=["Uhr", "Regen mm", "Temp °C"])
    def stil(c):
        return c.configure_view(stroke=None).configure_axis(
            labelFont=FONT, titleFont=FONT, labelColor=GREY_900, titleColor=GREY_600, gridColor="#F0F0F0"
        ).configure_legend(orient="top", title=None, labelFont=FONT)

    oben = alt.layer(band, linien, grenzen).resolve_scale(color="independent").properties(height=320)
    st.altair_chart(stil(oben), width="stretch")
    st.altair_chart(stil(regen.properties(height=150)), width="stretch")
    st.caption("Hintergrund je Stunde: grün flugtauglich, gelb nahe Grenze oder Regenrisiko, rot nicht flugtauglich "
               "(Regen ab 0,2 mm je Stunde).")


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

    _karten(tage[:7], p, markiert)
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

    if len(tage) > 7:
        with st.expander(f"Weitere {len(tage) - 7} Tage"):
            _karten(tage[7:], p, markiert)
            st.caption("Ab etwa einer Woche ist die Vorhersage nur noch grob.")

    # Schalter statt Aufklappbereich: Diagramme in zugeklappten Bereichen werden mit falscher Höhe gezeichnet
    if st.toggle("Stündliche Werte anzeigen", key="wx_stunden"):
        with st.container(border=True):
            _stunden(tage, p, fenster[0]["erntetag"]["datum"] if fenster else tage[0]["datum"])

    st.caption("Vorhersage: Open-Meteo (CC BY 4.0) für Lage und Höhe des Einsatzorts. Im Gebirge sind Talwinde "
               "und Gewitter schwer vorherzusagen, ab etwa 5 bis 7 Tagen nimmt die Genauigkeit deutlich ab. "
               "Planungshilfe, die Entscheidung trifft der Pilot vor Ort.")
