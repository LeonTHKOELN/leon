"""Analyse · Sensitivität, Break-even und Szenariovergleich für den aktuellen Auftrag."""
import altair as alt
import pandas as pd
import streamlit as st

from core import analyse
from core.fmt import de
from ui import state
from ui.components import badge, footer, kpi_html, kpis, note, section_title, simple_head
from ui.theme import FONT, GREY_400, GREY_600, GREY_900, INK, ORANGE

S, REG, GRUPPEN = state.S, state.REG, state.GRUPPEN
R = state.result()
p, HEU = R["p"], R["usecase"] == "Heuernte" and R.get("heu") and R["heu"]["ok"]
FARBEN = alt.Scale(domain=analyse.METHODEN, range=[ORANGE, GREY_400, GREY_900])
GRUPPE_TITEL = {g.id: g.titel for g in GRUPPEN}


def euro(v):
    return f"{de(v)} €"


def cfg(chart):
    return chart.configure_view(stroke=None).configure_axis(
        labelFont=FONT, titleFont=FONT, labelColor=GREY_900, titleColor=GREY_600, gridColor="#F0F0F0"
    ).configure_legend(labelFont=FONT, titleFont=FONT, orient="top", title=None)


simple_head("Analyse", "Sensitivität & Break-even",
            f"Use Case {R['usecase']} · Welche Annahmen entscheiden, und ab wann lohnt sich die Drohne?")

m, k = analyse.guenstigstes(R)
alt_best = min(k["Helikopter"], k["Tragen"])
vorteil = alt_best - k["Drohne"]
kpis([kpi_html("Günstigstes Verfahren", m, "", " · ".join(f"{x} {euro(v)}" for x, v in k.items()), accent=True),
      kpi_html("Drohne gegenüber bester Alternative", ("+" if vorteil >= 0 else "−") + de(abs(vorteil)), "€",
               "günstiger" if vorteil >= 0 else "teurer"),
      kpi_html("Szenario", S.szenario, "", f"{len(state.changed_keys())} Werte abweichend von der Basis")])
st.write("")

tab_s, tab_b, tab_z = st.tabs(["Sensitivität", "Break-even", "Szenarien"])

# ---------------------------------------------------------------------------
# Sensitivität
# ---------------------------------------------------------------------------
with tab_s:
    c1, c2 = st.columns([3, 2])
    ziel = c1.selectbox("Zielgröße", list(analyse.ZIELE), key="an_ziel", help="Welche Größe wird betrachtet")
    delta = c2.slider("Veränderung je Parameter", 5, 50, 20, 5, format="±%d %%", key="an_delta") / 100
    basis, rows = analyse.sensitivitaet(R, REG, ziel, delta)
    st.caption(f"{analyse.ZIELE[ziel]} · aktueller Wert {euro(basis)}. Jeder Parameter wird einzeln um "
               f"±{de(delta * 100)} % verändert, alle anderen bleiben gleich.")
    if not rows:
        note("Keine Parameter mit Wirkung auf diese Größe.")
    else:
        top = rows[:12]
        df = pd.DataFrame([{"Parameter": f"{r['Parameter']} ({r['Einheit']})", "Richtung": lbl,
                            "Δ": r[col], "Wert": r[wcol], "txt": ("+" if r[col] >= 0 else "−") + de(abs(r[col])) + " €"}
                           for r in top for lbl, col, wcol in [(f"−{de(delta * 100)} %", "Δ niedrig", "niedrig"),
                                                               (f"+{de(delta * 100)} %", "Δ hoch", "hoch")]])
        order = [f"{r['Parameter']} ({r['Einheit']})" for r in top]
        bars = alt.Chart(df).mark_bar(cornerRadius=3).encode(
            y=alt.Y("Parameter:N", sort=order, title=None, axis=alt.Axis(labelLimit=320)),
            x=alt.X("Δ:Q", title=f"Veränderung {ziel} in €",
                    axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
            color=alt.Color("Richtung:N", sort=[f"−{de(delta * 100)} %", f"+{de(delta * 100)} %"],
                            scale=alt.Scale(domain=[f"−{de(delta * 100)} %", f"+{de(delta * 100)} %"],
                                            range=[GREY_400, ORANGE])),
            yOffset=alt.YOffset("Richtung:N", sort=[f"−{de(delta * 100)} %", f"+{de(delta * 100)} %"]),
            tooltip=["Parameter", "Richtung", alt.Tooltip("txt:N", title="Wirkung"),
                     alt.Tooltip("Wert:Q", format=",.2f", title="Parameterwert")])
        nulllinie = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
        st.altair_chart(cfg((bars + nulllinie).properties(height=alt.Step(15))), width="stretch")

        unbelegt = [r for r in top[:8] if S[f"m.{r['key']}"]["status"] == "Annahme"]
        if unbelegt:
            note("<b>Diese Annahmen zuerst validieren</b> (große Wirkung, noch nicht belegt): "
                 + ", ".join(r["Parameter"] for r in unbelegt[:5]) + ".", icon="!")
        st.caption("Ungleich lange Balken bedeuten Sprünge: Ab einer Grenze wird z. B. ein zusätzlicher Flug, "
                   "eine weitere Anfahrt oder ein weiterer Einsatztag nötig.")
        with st.expander("Alle Parameter mit Wirkung"):
            tab = pd.DataFrame([{"Parameter": r["Parameter"], "Gruppe": GRUPPE_TITEL.get(r["Gruppe"], r["Gruppe"]),
                                 "Wert": f"{de(r['Wert'], 2)} {r['Einheit']}",
                                 f"−{de(delta * 100)} %": euro(r["Δ niedrig"]),
                                 f"+{de(delta * 100)} %": euro(r["Δ hoch"]),
                                 "Status": S[f"m.{r['key']}"]["status"]} for r in rows])
            st.dataframe(tab, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Break-even
# ---------------------------------------------------------------------------
with tab_b:
    num_keys = [k for g in GRUPPEN for k in g.keys
                if REG[k].typ != "bool" and k not in analyse.NICHT_VARIIEREN]
    optionen = ([analyse.FLAECHE] if HEU else []) + num_keys
    standard = analyse.FLAECHE if HEU else "drohne.nutzlast_kg"

    def label(k):
        if k == analyse.FLAECHE:
            return "Wiesenfläche (ha)"
        return f"{REG[k].label} ({REG[k].einheit}) · {GRUPPE_TITEL.get(REG[k].gruppe, '')}"

    c1, c2 = st.columns([3, 2])
    if S.get("an_x") not in optionen:
        S.an_x = standard
    key = c1.selectbox("x-Achse", optionen, key="an_x", format_func=label)
    if key == analyse.FLAECHE:
        aktuell, lo, hi, einheit, titel = R["heu"]["flaeche_ha"], 0.25, 10.0, "ha", "Wiesenfläche"
    else:
        prm = REG[key]
        aktuell, einheit, titel = p[key], prm.einheit, prm.label
        lo = max(prm.min if prm.min is not None else 0, aktuell * 0.25 if aktuell else 0)
        hi = min(prm.max if prm.max is not None else aktuell * 3, aktuell * 3 if aktuell else 10)
        if hi <= lo:
            lo, hi = (prm.min or 0), (prm.max or 10)
    lo, hi = c2.slider("Bereich", float(lo if key != analyse.FLAECHE else 0.1), float(hi * (1.0 if key != analyse.FLAECHE else 2)),
                       (float(lo), float(hi)), key=f"an_rng_{key}")
    n = 30
    werte = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    rows = analyse.sweep(R, REG, key, werte)
    df = pd.DataFrame(rows).melt(id_vars="x", var_name="Verfahren", value_name="Kosten")
    df["txt"] = df["Kosten"].apply(euro)
    df["xtxt"] = df["x"].apply(lambda v: f"{de(v, 2)} {einheit}")
    linien = alt.Chart(df).mark_line(strokeWidth=3, interpolate="step-after" if REG.get(key) and REG[key].typ == "int"
                                     else "linear").encode(
        x=alt.X("x:Q", title=f"{titel} ({einheit})", scale=alt.Scale(nice=False),
                axis=alt.Axis(labelExpr="replace(format(datum.value, ',.2~f'), '.', ',')")),
        y=alt.Y("Kosten:Q", title="Kosten in €",
                axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
        color=alt.Color("Verfahren:N", scale=FARBEN),
        tooltip=[alt.Tooltip("xtxt:N", title=titel), "Verfahren", alt.Tooltip("txt:N", title="Kosten")])
    jetzt = alt.Chart(pd.DataFrame({"x": [aktuell]})).mark_rule(strokeDash=[5, 4], color=GREY_600).encode(x="x:Q")
    marken = []
    for a, b in [("Drohne", "Tragen"), ("Drohne", "Helikopter")]:
        for x, txt in analyse.schnittpunkte(rows, a, b):
            y = next(r for r in rows if r["x"] >= x)[a] if any(r["x"] >= x for r in rows) else rows[-1][a]
            marken.append({"x": x, "y": y, "Text": f"{a} = {b} bei {de(x, 2)} {einheit}"})
    layers = [linien, jetzt]
    if marken:
        mk = pd.DataFrame(marken)
        layers.append(alt.Chart(mk).mark_point(shape="diamond", size=120, filled=True, color=INK).encode(
            x="x:Q", y="y:Q", tooltip=["Text"]))
    st.altair_chart(cfg(alt.layer(*layers).properties(height=360)), width="stretch")
    st.caption(f"Gestrichelt: aktueller Wert ({de(aktuell, 2)} {einheit}). Raute: Gleichstand zweier Verfahren.")
    if marken:
        for mrk in marken:
            st.markdown(f"- **{mrk['Text']}**")
    else:
        note("Im gewählten Bereich gibt es keinen Gleichstand zwischen Drohne und den anderen Verfahren. "
             "Bereich erweitern oder anderen Parameter wählen.")
    if HEU and key == analyse.FLAECHE:
        st.caption("Die Wiesenfläche wird bei gleicher Lage und Neigung skaliert. Sprünge entstehen, wenn ein "
                   "weiterer Mäh- oder Erntetag nötig wird.")

# ---------------------------------------------------------------------------
# Szenarien
# ---------------------------------------------------------------------------
with tab_z:
    out = analyse.szenarien(R, REG, state.SZENARIEN)
    df = pd.DataFrame(out)
    lang = df.melt(id_vars="Szenario", value_vars=analyse.METHODEN, var_name="Verfahren", value_name="Kosten")
    lang["txt"] = lang["Kosten"].apply(euro)
    chart = alt.Chart(lang).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Szenario:N", sort=list(df["Szenario"]), title=None, axis=alt.Axis(labelAngle=0, labelLimit=160)),
        xOffset=alt.XOffset("Verfahren:N", sort=analyse.METHODEN),
        y=alt.Y("Kosten:Q", title="Kosten in €", axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
        color=alt.Color("Verfahren:N", scale=FARBEN),
        tooltip=["Szenario", "Verfahren", alt.Tooltip("txt:N", title="Kosten")])
    st.altair_chart(cfg(chart.properties(height=320)), width="stretch")
    tab = df.copy()
    for col in analyse.METHODEN:
        tab[col] = tab[col].apply(euro)
    tab["Zeit Drohne h"] = tab["Zeit Drohne h"].apply(lambda v: de(v, 1))
    tab["CO₂ Drohne kg"] = tab["CO₂ Drohne kg"].apply(lambda v: de(v, 1))
    st.dataframe(tab, hide_index=True, width="stretch")
    st.caption("Szenarien starten jeweils von den Basiswerten (config/szenarien.yaml). „Aktueller Stand“ enthält "
               "deine Änderungen. Alle Werte sind Szenarioannahmen, keine Prognosen.")
    st.markdown(" ".join(badge("Annahme") for _ in range(1)) + f"<span style='color:{GREY_600};font-size:.85rem'> "
                "Zukunftsszenarien (z. B. 2035 autonom) sind hypothetisch, technische und rechtliche Zulässigkeit "
                "offen.</span>", unsafe_allow_html=True)
footer()
