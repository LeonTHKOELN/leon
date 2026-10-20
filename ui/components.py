"""Wiederverwendbare Bausteine der Oberfläche."""
import html

import streamlit as st

from core.fmt import de
from ui import state
from ui.theme import GREY_400


def page_head(path, title, lead):
    """Kopf einer Planungsseite mit Stepper."""
    paths = [p for p, _ in state.PLAN_PAGES]
    idx = paths.index(path)
    steps = []
    for i, (_, label) in enumerate(state.PLAN_PAGES):
        cls = "active" if i == idx else ("done" if i < idx else "")
        mark = "✓" if i < idx else str(i + 1)
        steps.append(f'<div class="lp-step {cls}"><div class="dot">{mark}</div>{label}</div>')
        if i < len(state.PLAN_PAGES) - 1:
            steps.append(f'<div class="lp-line {"done" if i < idx else ""}"></div>')
    st.markdown(
        f"""<div class="lp-top"><div class="lp-eyebrow">Schritt {idx + 1} von {len(paths)} · {state.PLAN_PAGES[idx][1]}</div>
        <div class="lp-steps">{''.join(steps)}</div></div>
        <div class="lp-h1">{title}</div><div class="lp-lead">{lead}</div>
        <div class="lp-rule" style="margin-top:16px"></div>""",
        unsafe_allow_html=True,
    )


def simple_head(eyebrow, title, lead):
    st.markdown(f"""<div class="lp-eyebrow">{eyebrow}</div><div class="lp-h1">{title}</div>
        <div class="lp-lead">{lead}</div><div class="lp-rule" style="margin-top:16px"></div>""",
                unsafe_allow_html=True)


def nav(path, next_label="Weiter"):
    paths = [p for p, _ in state.PLAN_PAGES]
    idx = paths.index(path)
    st.write("")
    c1, _, c3 = st.columns([1, 3, 1])
    if idx > 0 and c1.button("← Zurück", width="stretch"):
        st.switch_page(paths[idx - 1])
    if idx < len(paths) - 1 and c3.button(f"{next_label} →", type="primary", width="stretch"):
        st.switch_page(paths[idx + 1])


def kpi_html(k, v, unit="", s="", accent=False):
    return (f'<div class="lp-kpi {"accent" if accent else ""}"><div class="k">{k}</div>'
            f'<div class="v">{v}<small>{unit}</small></div><div class="s">{s}</div></div>')


def kpis(cards, two=False):
    st.markdown(f'<div class="lp-kpis {"two" if two else ""}">{"".join(cards)}</div>', unsafe_allow_html=True)


def note(text, warn=False, icon="i"):
    st.markdown(f'<div class="lp-note {"warn" if warn else ""}"><div class="ic">{icon}</div>'
                f'<div>{text}</div></div>', unsafe_allow_html=True)


def dg_note():
    note("<b>Gefahrgut an Bord.</b> Akkus und Kraftstoff gelten als Fracht als Gefahrgut. "
         "Flug nur in der Specific-Kategorie mit Betriebsgenehmigung. Einstufung im Einzelfall "
         "durch die Behörde (z. B. Austro Control) klären.", warn=True, icon="!")


def section_title(t):
    st.markdown(f'<div class="lp-card-title" style="margin-top:6px">{t}</div>', unsafe_allow_html=True)


def badge(status):
    return f'<span class="lp-badge {status}">{status}</span>'


def calc_card(tr):
    """Rechenweg einer Rechnung als Tabelle."""
    rows = []
    for s in tr.steps:
        k = f'<span class="c">{html.escape(s.kommentar)}</span>' if s.kommentar else ""
        rows.append(f"<tr><td><b>{html.escape(s.titel)}</b>{k}</td><td class='f'>{html.escape(s.formel)}</td>"
                    f"<td class='e'>{html.escape(s.einsetzung)}</td><td class='r'>{html.escape(s.ergebnis)}</td></tr>")
    st.markdown(
        f"""<div class="lp-calc-head"><div class="lp-calc-title">{html.escape(tr.titel)}</div></div>
        <div class="lp-calc-desc">{html.escape(tr.beschreibung)}</div>
        <table class="lp-calc"><thead><tr><th style="width:20%">Schritt</th><th style="width:34%">Formel</th>
        <th>Eingesetzt</th><th style="text-align:right">Ergebnis</th></tr></thead><tbody>{''.join(rows)}</tbody></table>""",
        unsafe_allow_html=True)


def footer():
    st.markdown(
        "<div class='lp-footer'>Konzeptprototyp · TH Köln × STIHL · Projekt Arbeiten in Steillagen · "
        "Alle Werte sind Annahmen und ersetzen keine Flugplanung oder behördliche Genehmigung.<br>"
        "Höhendaten: EU-DEM v1.1 über OpenTopoData · Copernicus DEM GLO-90 über Open-Meteo "
        "(© DLR e.V. 2010–2014 und © Airbus Defence and Space GmbH 2014–2018, bereitgestellt im Rahmen "
        "des Copernicus-Programms).</div>",
        unsafe_allow_html=True,
    )


__all__ = ["de", "GREY_400"]
