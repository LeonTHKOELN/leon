"""Parameter-Registry: lädt parameter.yaml und szenarien.yaml."""
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parent.parent / "config"
STATUS = ["Annahme", "Literaturwert", "Herstellerangabe", "Regelwerk", "Validiert"]


@dataclass
class Param:
    key: str
    gruppe: str
    label: str
    einheit: str
    wert: object
    typ: str = "float"
    min: float | None = None
    max: float | None = None
    step: float | None = None
    status: str = "Annahme"
    quelle: str = ""
    kommentar: str = ""

    def clamp(self, v):
        """Wert in Typ und zulässigen Bereich bringen."""
        if self.typ == "bool":
            return bool(v)
        v = float(v)
        if self.min is not None:
            v = max(v, self.min)
        if self.max is not None:
            v = min(v, self.max)
        return int(round(v)) if self.typ == "int" else v


@dataclass
class Gruppe:
    id: str
    titel: str
    beschreibung: str
    keys: list


def load_registry(path: Path = CONFIG / "parameter.yaml"):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    params, gruppen = {}, []
    for g in data["gruppen"]:
        keys = []
        for raw in g["parameter"]:
            p = Param(gruppe=g["id"], **raw)
            if p.key in params:
                raise ValueError(f"Parameter doppelt definiert: {p.key}")
            if p.status not in STATUS:
                raise ValueError(f"Unbekannter Status bei {p.key}: {p.status}")
            p.wert = p.clamp(p.wert)
            params[p.key] = p
            keys.append(p.key)
        gruppen.append(Gruppe(g["id"], g["titel"], g.get("beschreibung", ""), keys))
    return params, gruppen


def defaults(params) -> dict:
    return {k: p.wert for k, p in params.items()}


def load_scenarios(path: Path = CONFIG / "szenarien.yaml"):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["szenarien"]


def scenario_values(params, scenario) -> dict:
    """Basiswerte plus Abweichungen des Szenarios. Unbekannte Keys führen zu einem Fehler."""
    vals = defaults(params)
    for k, v in (scenario.get("werte") or {}).items():
        if k not in params:
            raise KeyError(f"Szenario {scenario.get('id')}: unbekannter Parameter {k}")
        vals[k] = params[k].clamp(v)
    return vals
