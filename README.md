# Lift Planner

Konzeptprototyp aus dem Projekt **TH Köln × STIHL · Arbeiten in Steillagen** (Kernkonzept Drohnen-Transportbox).

Die App plant einen Materialtransport per Schwerlastdrohne in vier Schritten:

1. **Auftrag** · Landeplatz, Einsatzort, Höhendifferenz, Team
2. **Ausrüstung** · Geräte und Energieversorgung (Akku, Benzin oder beides)
3. **Flugplan** · Packen in Boxen, Verteilung auf Flüge, Gefahrgut getrennt, Packliste als CSV
4. **Einsparungen** · Vergleich Drohne, Helikopter und Tragen nach Kosten, Zeit und CO₂

Alle Werte sind Beispielwerte und lassen sich in der Seitenleiste unter **Annahmen** anpassen.
Die App ersetzt keine Flugplanung und keine behördliche Genehmigung.

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Online stellen (GitHub + Streamlit Community Cloud)

1. Neues Repository auf GitHub anlegen und `app.py`, `requirements.txt`, `README.md` und den Ordner `.streamlit/` hochladen.
2. Auf [share.streamlit.io](https://share.streamlit.io) mit GitHub anmelden.
3. **Create app** wählen, Repository und Branch auswählen, Main file `app.py`.
4. Deploy. Die App bekommt eine eigene URL zum Teilen.

## Hinweis

Studentisches Konzept, kein offizielles STIHL-Produkt.
