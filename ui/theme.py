"""Farben und globales Styling (STIHL Light Theme)."""
import re
from pathlib import Path

import streamlit as st

ORANGE = "#FF6600"
ORANGE_DARK = "#E05A00"
ORANGE_LIGHT = "#FFF3EB"
INK = "#1F1F1F"
GREY_900 = "#2B2B2B"
GREY_600 = "#6B6B6B"
GREY_400 = "#A8A8A8"
GREY_200 = "#E6E6E6"
GREY_100 = "#F4F4F4"
FONT = "Barlow, Arial, sans-serif"

_RAW = (Path(__file__).parent / "theme.css").read_text(encoding="utf-8")
# Kommentare und Leerzeilen entfernen: Streamlit würde den Block sonst als Markdown-Text ausgeben
_CSS = "\n".join(line for line in re.sub(r"/\*.*?\*/", "", _RAW, flags=re.S).splitlines() if line.strip())
_FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700'
          '&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">')


def inject():
    st.markdown(f"{_FONTS}<style>{_CSS}</style>", unsafe_allow_html=True)
