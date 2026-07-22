from functools import lru_cache
from pathlib import Path

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"


@lru_cache
def load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


@lru_cache
def load_stylesheet(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def template(name: str, **context: object) -> str:
    return load_template(name).format_map(context)


def inject_styles(*names: str) -> None:
    css = "\n".join(load_stylesheet(name) for name in names)
    st.markdown(template("stylesheet.html", css=css), unsafe_allow_html=True)


def inject_theme() -> None:
    inject_styles("theme.css")


def render_brand() -> None:
    st.markdown(load_template("brand.html"), unsafe_allow_html=True)


def radar_art() -> str:
    return load_template("radar.html")
