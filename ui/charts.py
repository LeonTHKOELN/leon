"""Diagramme (Altair)."""
import altair as alt
import pandas as pd

from core.fmt import de
from ui.theme import FONT, GREY_100, GREY_200, GREY_400, GREY_600, GREY_900, INK, ORANGE


def profile_chart(P):
    clear, ceiling = P["clear"], P["ceiling"]
    df = pd.DataFrame({
        "km": [d / 1000 for d in P["ds"]], "terrain": P["terrain"], "path": P["path"],
        "direct": P["direct"],
        "lo": [t + clear for t in P["terrain"]], "hi": [t + ceiling for t in P["terrain"]],
    })
    df["Distanz"] = df["km"].apply(lambda v: f"{de(v, 2)} km")
    df["Gelände"] = df["terrain"].apply(lambda v: f"{de(v)} m ü. NN")
    df["Flughöhe"] = df["path"].apply(lambda v: f"{de(v)} m ü. NN")
    df["Über Grund"] = (df["path"] - df["terrain"]).apply(lambda v: f"{de(v)} m")
    ymin = min(P["terrain"]) - 25
    ymax = max(max(df["hi"]) if P["real"] else max(P["path"]), max(P["path"])) + 15
    ys = alt.Scale(domain=[ymin, ymax], nice=False, zero=False)
    x = alt.X("km:Q", title="Distanz (km)", scale=alt.Scale(nice=False),
              axis=alt.Axis(grid=False, tickCount=8,
                            labelExpr="replace(format(datum.value, '.1f'), '.', ',')"))
    base = alt.Chart(df).encode(x=x)
    hover = alt.selection_point(fields=["km"], nearest=True, on="mouseover", empty=False, clear="mouseout")
    layers = [
        base.mark_area(color=ORANGE, opacity=.09, clip=True).encode(
            y=alt.Y("lo:Q", scale=ys, title="Höhe (m ü. NN)",
                    axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")), y2="hi:Q"),
        base.mark_area(color="#E4DED4", clip=True, line={"color": "#8C8273", "strokeWidth": 1.6}).encode(
            y=alt.Y("terrain:Q", scale=ys)),
        base.mark_line(color=GREY_600, strokeDash=[6, 5], strokeWidth=1.4, clip=True).encode(
            y=alt.Y("direct:Q", scale=ys)),
        base.mark_line(color=ORANGE, strokeWidth=3, clip=True).encode(y=alt.Y("path:Q", scale=ys)),
        base.mark_rule(color=GREY_900, strokeWidth=1).encode(
            opacity=alt.condition(hover, alt.value(.5), alt.value(0)),
            tooltip=["Distanz", "Gelände", "Flughöhe", "Über Grund"]).add_params(hover),
        base.mark_circle(color=ORANGE, size=70, stroke="white", strokeWidth=2).encode(
            y=alt.Y("path:Q", scale=ys), opacity=alt.condition(hover, alt.value(1), alt.value(0))),
    ]
    return (alt.layer(*layers).properties(height=320)
            .configure_view(stroke=None)
            .configure_axis(labelFont=FONT, titleFont=FONT,
                            labelColor=GREY_600, titleColor=GREY_600, titleFontWeight=600,
                            domainColor=GREY_200, tickColor=GREY_200, gridColor=GREY_100))


def compare_chart(df, metric, nd):
    """Balkendiagramm Drohne / Helikopter / Tragen für eine Kennzahl."""
    df = df.copy()
    df["txt"] = df[metric].apply(lambda v: de(v, nd))
    color = alt.Scale(domain=["Drohne", "Helikopter", "Tragen"], range=[ORANGE, GREY_400, GREY_900])
    base = alt.Chart(df).encode(
        x=alt.X("Variante:N", sort=None, title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=12, labelColor=GREY_900, ticks=False, domain=False)),
        y=alt.Y(f"{metric}:Q", title=None, axis=None,
                scale=alt.Scale(domainMax=max(df[metric].max() * 1.18, 1))),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=46).encode(
        color=alt.Color("Variante:N", scale=color, legend=None),
        tooltip=["Variante", alt.Tooltip("txt:N", title=metric)])
    text = base.mark_text(dy=-9, fontSize=13, fontWeight=700, color=INK, font=FONT).encode(text="txt:N")
    return (bars + text).properties(height=230).configure_view(stroke=None).configure_axis(labelFont=FONT, grid=False)
