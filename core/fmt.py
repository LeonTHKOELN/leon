"""Zahlenformat für Anzeige und Rechenweg (deutsches Format: 1.234,5)."""


def de(x: float, nd: int = 0) -> str:
    t = f"{x:,.{nd}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_min(m: float) -> str:
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"
