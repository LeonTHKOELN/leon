# Lift Planner

Konzeptprototyp aus dem Projekt **TH Köln × STIHL · Arbeiten in Steillagen**.
Plant Materialtransporte mit Lastendrohnen in Steillagen und vergleicht sie mit Helikopter und Tragen.

## Aufbau

```
app.py                  Einstieg, Navigation
config/
  parameter.yaml        ALLE Rechenwerte mit Einheit, Bereich, Status, Quelle, Kommentar
  szenarien.yaml        Szenarien = Abweichungen von den Basiswerten
core/                   Rechenkern ohne Oberfläche (testbar)
  geo.py                Entfernungen, Stützpunkte
  hoehe.py              Höhen-API (EU-DEM, Fallback Copernicus)
  profil.py             Flughöhe, Flugweg, Flugzeit
  packen.py             Boxen und Flugeinteilung
  kosten.py             Drohne, Helikopter, Tragen
  modell.py             Gesamtrechnung
  trace.py              Rechenweg-Protokoll
ui/                     Theme, Bausteine, Diagramme, Sitzungszustand
views/                  eine Datei je Seite
tests/                  automatische Tests für den Rechenkern
assets/                 Logo
```

**Grundprinzip:** Der Rechenkern liest Werte nur aus den Parametern und schreibt bei jeder Rechnung
den Rechenweg mit. Die Seite *Annahmen & Parameter* zeigt diesen Rechenweg an. So entspricht die
angezeigte Rechnung immer exakt der Rechnung der App.

## Neue Variable hinzufügen

1. Eintrag in `config/parameter.yaml` in der passenden Gruppe anlegen (key, label, einheit, wert, min, max, status, quelle).
2. Im Rechenkern über `p["dein.key"]` verwenden und mit `trace.add(...)` im Rechenweg ausweisen.

Die Variable erscheint automatisch auf der Seite *Annahmen & Parameter*.

## Szenarien

- In der App: *Annahmen & Parameter › Szenario laden*.
- Eigene Werte als JSON exportieren und später wieder importieren (Streamlit Cloud speichert nichts dauerhaft).
- Dauerhaft im Repo: *Speichern / Laden › Als Szenario für szenarien.yaml* und den Inhalt in `config/szenarien.yaml` einfügen.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest -q        # Tests (benötigt pytest)
```

## Online (GitHub + Streamlit Community Cloud)

Repository auf share.streamlit.io verbinden, Main file `app.py`.

## Hinweis

Studentisches Konzept, kein offizielles STIHL-Produkt. Alle Werte sind Annahmen, solange sie nicht als
validiert gekennzeichnet sind. Die App ersetzt keine Flugplanung und keine behördliche Genehmigung.

Höhendaten: EU-DEM v1.1 über OpenTopoData · Copernicus DEM GLO-90 über Open-Meteo
(© DLR e.V. 2010–2014 und © Airbus Defence and Space GmbH 2014–2018, bereitgestellt im Rahmen des Copernicus-Programms).
