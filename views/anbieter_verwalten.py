"""Einstellungen · Anbieter: Liste der Drohnen-Dienstleister und Heli-Basen verwalten.

Änderungen gelten für die laufende Sitzung. Dauerhaft: CSV exportieren und als data/anbieter.csv ins Repo legen.
"""
import pandas as pd
import streamlit as st

from core import anbieter as anb
from core.fmt import de
from ui import state
from ui.components import footer, note, section_title, simple_head

S = state.S

PREISFELDER = [("pauschale_eur", "Anfahrtspauschale €", "anreise.pauschale_eur"),
               ("eur_km", "€/km", "anreise.eur_km"),
               ("fahrt_eur_h", "Fahrzeit €/h je Person", "dl.fahrt_eur_h"),
               ("einsatz_eur_h", "Einsatz €/h", "dl.einsatz_eur_h"),
               ("heli_eur_min", "Heli €/min", "heli.eur_min"),
               ("heli_mindest_min", "Heli Mindestabrechnung min", "heli.mindest_min"),
               ("heli_bereitstellung_eur", "Heli Bereitstellung €", "heli.bereitstellung_eur")]


def add_anbieter():
    name, adresse = S.na_name.strip(), S.na_adresse.strip()
    if not name or not adresse:
        S.anb_msg = ("warn", "Name und Adresse angeben.")
        return
    try:
        lat, lon = state._geocode(adresse)
    except Exception as e:  # noqa: BLE001
        S.anb_msg = ("warn", f"Adresse nicht gefunden oder Suche nicht erreichbar: {e}")
        return
    neu = {k: None for k in anb.SPALTEN}
    neu.update({"id": f"neu_{len(S.anbieter_liste) + 1}", "name": name, "typ": S.na_typ, "adresse": adresse,
                "lat": round(lat, 6), "lon": round(lon, 6), "fiktiv": S.na_fiktiv, "kommentar": "In der App angelegt"})
    for col, _, _ in PREISFELDER:
        v = S.get(f"na_{col}")
        neu[col] = float(v) if v not in (None, 0, 0.0) else None
    S.anbieter_liste = S.anbieter_liste + [neu]
    S.anb_msg = ("ok", f"„{name}“ angelegt ({de(lat, 5)}, {de(lon, 5)}).")


def remove(aid):
    S.anbieter_liste = [a for a in S.anbieter_liste if a["id"] != aid]


def reset_list():
    S.anbieter_liste = state.load_anbieter()
    S.anb_msg = ("ok", "Anbieterliste aus data/anbieter.csv neu geladen.")


simple_head("Einstellungen", "Anbieter",
            "Drohnen-Dienstleister und Helikopter-Basen. Leere Preisfelder verwenden die Standardwerte "
            "aus Annahmen & Parameter.")
msg = S.get("anb_msg")
if msg:
    note(msg[1], warn=msg[0] == "warn", icon="!" if msg[0] == "warn" else "✓")
    S.anb_msg = None

liste = state.anbieter_mit_koordinaten()
p = state.params()
rows = []
for a in liste:
    row = {"Name": a["name"], "Typ": a["typ"], "Adresse": a["adresse"], "fiktiv": "ja" if a["fiktiv"] else "",
           "Koordinaten": f"{a['lat']:.5f}, {a['lon']:.5f}", "Herkunft Koordinaten": a["koord_quelle"]}
    for col, label, key in PREISFELDER:
        if (a["typ"] == "Helikopter") == col.startswith("heli_"):
            v = a.get(col)
            row[label] = de(v, 2) if v is not None else f"Standard ({de(p[key], 2)})"
    rows.append(row)
section_title("Hinterlegte Anbieter")
st.dataframe(pd.DataFrame(rows).fillna("–"), hide_index=True, width="stretch")

c1, c2, c3 = st.columns([2, 2, 1])
c1.download_button("Liste als CSV exportieren", anb.to_csv(S.anbieter_liste), file_name="anbieter.csv",
                   mime="text/csv", width="stretch",
                   help="Datei als data/anbieter.csv ins Repo legen, damit die Änderungen dauerhaft gelten")
c2.button("Liste aus Datei neu laden", on_click=reset_list, width="stretch")
neu = [a for a in S.anbieter_liste if str(a["id"]).startswith("neu_")]
if neu:
    with c3.popover("Entfernen", width="stretch"):
        for a in neu:
            st.button(a["name"], key=f"rm_{a['id']}", on_click=remove, args=(a["id"],), width="stretch")

st.write("")
section_title("Anbieter hinzufügen")
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    c1.text_input("Name", key="na_name", placeholder="z. B. Drohnenservice Muster GmbH")
    c2.selectbox("Typ", anb.TYPEN, key="na_typ")
    c3.checkbox("fiktiv", key="na_fiktiv")
    st.text_input("Adresse", key="na_adresse", placeholder="Straße Nr, PLZ Ort, Land",
                  help="Koordinaten werden über OpenStreetMap (Nominatim) gesucht")
    st.caption("Preise optional. 0 oder leer = Standardwert verwenden.")
    felder = [f for f in PREISFELDER if (S.get("na_typ", "Drohne") == "Helikopter") == f[0].startswith("heli_")]
    cols = st.columns(len(felder))
    for col, (key, label, pkey) in zip(cols, felder):
        col.number_input(label, 0.0, 100000.0, value=0.0, key=f"na_{key}", help=f"Standard: {de(p[pkey], 2)}")
    st.button("Adresse suchen und anlegen", type="primary", on_click=add_anbieter)
note("Änderungen gelten nur für diese Sitzung. Für dauerhafte Einträge die CSV exportieren und als "
     "<b>data/anbieter.csv</b> ins Repo legen.")
st.caption("Adresssuche: © OpenStreetMap-Mitwirkende, Nominatim. Routing: OSRM auf OpenStreetMap-Daten.")
footer()
