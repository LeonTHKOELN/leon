"""Einstellungen · Annahmen & Parameter.

Zentrale Datenbasis aller Rechnungen:
- Tab "Parameter": alle Werte je Gruppe editierbar, mit Status, Quelle und Kommentar
- Tab "Rechenweg": jede Rechnung mit Formel, eingesetzten Werten und Ergebnis
- Tab "Szenarien": hinterlegte Szenarien und ihre Abweichungen von der Basis
Szenarien lassen sich laden, der aktuelle Stand als Datei exportieren und wieder importieren.
"""
import json
from datetime import datetime

import pandas as pd
import streamlit as st
import yaml

from core import params as registry
from core.fmt import de
from ui import state
from ui.components import badge, calc_card, footer, note, simple_head
from ui.theme import GREY_600

S, REG, GRUPPEN, SZENARIEN = state.S, state.REG, state.GRUPPEN, state.SZENARIEN
STATUS = registry.STATUS


# ---------------------------------------------------------------------------
# Aktionen (Callbacks laufen vor dem nächsten Rendern)
# ---------------------------------------------------------------------------
def _refresh_editors():
    S.ed_ver += 1  # neue Editor-Instanzen, damit alte Bearbeitungsstände nicht nachwirken


def load_scenario():
    sc = next(s for s in SZENARIEN if s["name"] == S.sel_szenario)
    for k, v in registry.scenario_values(REG, sc).items():
        S[f"p.{k}"] = v
    S.szenario = sc["name"]
    S.param_msg = ("ok", f"Szenario „{sc['name']}“ geladen.")
    _refresh_editors()


def reset_all():
    for k, p in REG.items():
        S[f"p.{k}"] = p.wert
        S[f"m.{k}"] = state.meta_default(k)
    S.szenario = "Basis"
    S.param_msg = ("ok", "Alle Parameter auf die Basiswerte zurückgesetzt.")
    _refresh_editors()


def on_edit(gid, keys):
    edits = S[f"ed_{gid}_{S.ed_ver}"]["edited_rows"]
    clamped = []
    for idx, changes in edits.items():
        k = keys[int(idx)]
        for col, val in changes.items():
            if col == "Wert" and val is not None:
                new = REG[k].clamp(val)
                if abs(float(new) - float(val)) > 1e-9:
                    clamped.append(f"{REG[k].label} → {de(new, 2)} {REG[k].einheit}")
                S[f"p.{k}"] = new
            elif col in ("Status", "Quelle", "Kommentar"):
                S[f"m.{k}"] = {**S[f"m.{k}"], col.lower(): val or ""}
    if any("Wert" in c for c in edits.values()):
        S.szenario = "Eigene Werte"
    S.param_msg = ("warn", "Auf zulässigen Bereich begrenzt: " + "; ".join(clamped)) if clamped else None
    _refresh_editors()


def on_bool(k):
    S[f"p.{k}"] = bool(S[f"pw.{k}"])
    S.szenario = "Eigene Werte"


def export_json(with_job):
    data = {
        "app": "Lift Planner", "version": 1, "exportiert": datetime.now().isoformat(timespec="seconds"),
        "szenario": S.szenario,
        "parameter": {k: S[f"p.{k}"] for k in REG},
        "meta": {k: S[f"m.{k}"] for k in REG},
    }
    if with_job:
        data["auftrag"] = {k: S[k] for k in state.EXPORT_JOB_KEYS}
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_scenario_yaml(name):
    diff = {k: S[f"p.{k}"] for k in REG if S[f"p.{k}"] != REG[k].wert}
    entry = [{"id": name.lower().replace(" ", "_"), "name": name, "beschreibung": "In der App erstellt",
              "werte": diff}]
    return ("# In szenarien.yaml unter 'szenarien:' einfügen\n"
            + yaml.safe_dump(entry, allow_unicode=True, sort_keys=False))


def do_import():
    f = S.get("imp_file")
    if f is None:
        return
    try:
        data = json.loads(f.getvalue().decode("utf-8"))
        unknown = []
        for k, v in (data.get("parameter") or {}).items():
            if k in REG:
                S[f"p.{k}"] = REG[k].clamp(v)
            else:
                unknown.append(k)
        for k, m in (data.get("meta") or {}).items():
            if k in REG and isinstance(m, dict):
                S[f"m.{k}"] = {**state.meta_default(k), **{x: m.get(x, "") for x in ("status", "quelle", "kommentar")}}
        for k, v in (data.get("auftrag") or {}).items():
            if k in state.JOB_DEFAULTS:
                S[k] = v
        S.szenario = data.get("szenario") or "Import"
        msg = f"Datei „{f.name}“ geladen."
        if unknown:
            msg += f" Unbekannte Parameter ignoriert: {', '.join(unknown)}"
        S.param_msg = ("warn" if unknown else "ok", msg)
    except Exception as e:  # noqa: BLE001
        S.param_msg = ("warn", f"Datei konnte nicht gelesen werden: {e}")
    _refresh_editors()


# ---------------------------------------------------------------------------
# Seite
# ---------------------------------------------------------------------------
R = state.result()
simple_head("Einstellungen", "Annahmen & Parameter",
            "Zentrale Datenbasis aller Berechnungen. Jede Änderung wirkt sofort auf alle Seiten.")

changed = state.changed_keys()
counts = {s: sum(1 for k in REG if S[f"m.{k}"]["status"] == s) for s in STATUS}
st.markdown(
    f"<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px'>"
    f"<span style='color:{GREY_600};font-size:.86rem;margin-right:6px'>{len(REG)} Parameter · "
    f"Szenario <b>{S.szenario}</b> · {len(changed)} abweichend von der Basis</span>"
    + "".join(f"{badge(s)}<span style='color:{GREY_600};font-size:.8rem;margin-right:8px'>{n}</span>"
              for s, n in counts.items() if n)
    + "</div>", unsafe_allow_html=True)

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2], vertical_alignment="bottom")
    names = [s["name"] for s in SZENARIEN]
    c1.selectbox("Szenario", names, key="sel_szenario",
                 index=names.index(S.szenario) if S.szenario in names else 0,
                 help="Basis + hinterlegte Abweichungen aus config/szenarien.yaml")
    c2.button("Szenario laden", on_click=load_scenario, width="stretch", type="primary")
    c3.button("Alles zurücksetzen", on_click=reset_all, width="stretch")
    with c4.popover("Speichern / Laden", width="stretch"):
        with_job = st.checkbox("Auftrag (Route, Equipment) mitspeichern", value=True)
        st.download_button("Stand exportieren (JSON)", export_json(with_job),
                           file_name=f"liftplanner_{datetime.now():%Y%m%d_%H%M}.json",
                           mime="application/json", width="stretch")
        sc_name = st.text_input("Name für Szenario-Datei", value="Mein Szenario")
        st.download_button("Als Szenario für szenarien.yaml", export_scenario_yaml(sc_name),
                           file_name="szenario.yaml", mime="text/yaml", width="stretch",
                           help="Nur die Abweichungen von der Basis, zum dauerhaften Hinterlegen im Repo")
        st.file_uploader("Stand importieren (JSON)", type=["json"], key="imp_file", on_change=do_import)

msg = S.get("param_msg")
if msg:
    note(msg[1], warn=msg[0] == "warn", icon="!" if msg[0] == "warn" else "✓")
    S.param_msg = None

tab_p, tab_r, tab_s = st.tabs(["Parameter", "Rechenweg", "Szenarien"])

# ---------- Parameter ----------
with tab_p:
    st.caption("Wert, Status, Quelle und Kommentar direkt in der Tabelle ändern. "
               "Eingaben werden auf den zulässigen Bereich begrenzt.")
    for g in GRUPPEN:
        num_keys = [k for k in g.keys if REG[k].typ != "bool"]
        bool_keys = [k for k in g.keys if REG[k].typ == "bool"]
        n_changed = sum(1 for k in g.keys if k in changed)
        with st.container(border=True):
            tag = f' <span class="lp-badge Annahme">{n_changed} geändert</span>' if n_changed else ""
            st.markdown(f"<div class='lp-group-title'>{g.titel}{tag}</div>"
                        f"<div class='lp-group-desc'>{g.beschreibung}</div>", unsafe_allow_html=True)
            if num_keys:
                df = pd.DataFrame([{
                    "Parameter": REG[k].label,
                    "Wert": float(S[f"p.{k}"]),
                    "Einheit": REG[k].einheit,
                    "Basis": float(REG[k].wert),
                    "Δ": "●" if k in changed else "",
                    "Status": S[f"m.{k}"]["status"],
                    "Quelle": S[f"m.{k}"]["quelle"],
                    "Kommentar": S[f"m.{k}"]["kommentar"],
                } for k in num_keys])
                st.data_editor(
                    df, key=f"ed_{g.id}_{S.ed_ver}", hide_index=True, width="stretch",
                    on_change=on_edit, args=(g.id, num_keys),
                    column_config={
                        "Parameter": st.column_config.TextColumn(disabled=True, width="medium"),
                        "Wert": st.column_config.NumberColumn(width="small", required=True),
                        "Einheit": st.column_config.TextColumn(disabled=True, width="small"),
                        "Basis": st.column_config.NumberColumn(disabled=True, width="small"),
                        "Δ": st.column_config.TextColumn(disabled=True, width=40,
                                                         help="● = abweichend vom Basiswert"),
                        "Status": st.column_config.SelectboxColumn(options=STATUS, width="small", required=True),
                        "Quelle": st.column_config.TextColumn(width="large"),
                        "Kommentar": st.column_config.TextColumn(width="medium"),
                    },
                )
            for k in bool_keys:
                S[f"pw.{k}"] = bool(S[f"p.{k}"])
                st.toggle(f"{REG[k].label}  ·  Basis: {'ja' if REG[k].wert else 'nein'}", key=f"pw.{k}",
                          on_change=on_bool, args=(k,), help=f"{S[f'm.{k}']['quelle']}. {S[f'm.{k}']['kommentar']}")

# ---------- Rechenweg ----------
with tab_r:
    j, P = R["job"], R["P"]
    note("Der Rechenweg wird bei jeder Berechnung mitgeschrieben. Er zeigt also genau die Rechnung, "
         "die auch auf den Planungsseiten verwendet wird, mit den aktuell eingestellten Werten.")
    st.write("")
    with st.container(border=True):
        st.markdown("<div class='lp-calc-title'>Eingaben aus der Planung</div>"
                    "<div class='lp-calc-desc'>Auftragsdaten, die auf den Planungsseiten festgelegt werden.</div>",
                    unsafe_allow_html=True)
        geraete = ", ".join(f"{n} × {state.GERAETE[g]}" for g, n in j["anzahl"].items() if n) or "keine"
        energie = j["energie"] + (f" · {j['akkus']} Akkus" if j["energie"] != "Benzin-Lösung" else "") + \
            (f" · {de(j['liter'], 1)} l Kraftstoff" if j["energie"] != "Akku-Lösung" else "")
        rows = [("Landeplatz", f"{j['start'][0]:.5f}, {j['start'][1]:.5f} · {de(P['start_alt'])} m"),
                ("Einsatzort", f"{j['ziel'][0]:.5f}, {j['ziel'][1]:.5f} · {de(P['ziel_alt'])} m"),
                ("Team", f"{j['team']} Personen · Einsatzdauer {j['dauer_h']} h"),
                ("Geräte", geraete), ("Energie", energie), ("Höhenquelle", P["source"])]
        st.markdown("<table class='lp-calc'><tbody>" + "".join(
            f"<tr><td style='width:20%'><b>{a}</b></td><td>{b}</td></tr>" for a, b in rows) + "</tbody></table>",
                    unsafe_allow_html=True)
    for tr in R["traces"]:
        st.write("")
        with st.container(border=True):
            calc_card(tr)

# ---------- Szenarien ----------
with tab_s:
    st.caption("Szenarien sind in config/szenarien.yaml hinterlegt: Basiswerte plus Abweichungen. "
               "Eigene Szenarien über „Speichern / Laden“ als YAML exportieren und dort einfügen.")
    keys = sorted({k for s in SZENARIEN for k in (s.get("werte") or {})},
                  key=lambda k: list(REG).index(k))
    if keys:
        def fmt(k, v):
            if REG[k].typ == "bool":
                return "ja" if v else "nein"
            return de(v, 2).rstrip("0").rstrip(",")

        table = pd.DataFrame([{
            "Parameter": REG[k].label, "Einheit": REG[k].einheit, "Basis": fmt(k, REG[k].wert),
            **{s["name"]: fmt(k, (s.get("werte") or {}).get(k, REG[k].wert)) for s in SZENARIEN if s["id"] != "basis"},
            "Aktuell": fmt(k, S[f"p.{k}"]),
        } for k in keys])
        st.dataframe(table, hide_index=True, width="stretch")
    for s in SZENARIEN:
        st.markdown(f"**{s['name']}** · {s.get('beschreibung', '')}")

footer()
