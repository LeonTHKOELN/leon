"""Rechenweg: jede Rechnung protokolliert Formel, eingesetzte Werte und Ergebnis.

Die Seite "Annahmen & Parameter" zeigt diese Protokolle an. So ist garantiert, dass der
angezeigte Rechenweg exakt der Rechnung entspricht, die die App tatsächlich ausführt.
"""
from dataclasses import dataclass, field

from .fmt import de


@dataclass
class Step:
    titel: str
    formel: str
    einsetzung: str
    ergebnis: str
    kommentar: str = ""


@dataclass
class Trace:
    id: str
    titel: str
    beschreibung: str = ""
    steps: list = field(default_factory=list)

    def add(self, titel, formel, einsetzung, wert, einheit="", nd=1, kommentar="", text=None):
        """Schritt anhängen und den Wert unverändert zurückgeben (für Rechnen in einer Zeile)."""
        erg = text if text is not None else f"{de(wert, nd)} {einheit}".strip()
        self.steps.append(Step(titel, formel, einsetzung, erg, kommentar))
        return wert
