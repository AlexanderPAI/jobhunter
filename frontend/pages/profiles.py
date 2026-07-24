import asyncio
import html

import streamlit as st

from frontend.api import get_profiles
from frontend.auth import render_account_sidebar, require_auth
from frontend.ui import inject_theme, render_brand, template

st.set_page_config(page_title="Профили — КарьеРадар", page_icon="🟣", layout="wide")
require_auth()
inject_theme()

with st.sidebar:
    render_brand()
    render_account_sidebar()
    st.page_link("app.py", label="Новый радар")
    st.page_link("pages/profiles.py", label="Карьерные профили")


def short_summary(value: str | None) -> str:
    words = (value or "").split()
    summary = " ".join(words[:20])
    return f"{summary}…" if len(words) > 20 else summary


st.markdown(template("profiles_header.html"), unsafe_allow_html=True)

try:
    profiles = asyncio.run(get_profiles())
except Exception as error:
    st.error(f"Не удалось получить профили из базы данных: {error}")
    st.stop()

if not profiles:
    st.info(
        "Радар ещё не настроен. Загрузите резюме, чтобы создать первый карьерный профиль."
    )
    st.page_link("app.py", label="Настроить КарьеРадар")
    st.stop()

for profile in profiles:
    with st.container(border=True):
        main, action = st.columns([5, 1.2], vertical_alignment="center")
        with main:
            st.markdown(
                template(
                    "profile_list_name.html",
                    name=html.escape(profile.get("name") or "Без имени"),
                ),
                unsafe_allow_html=True,
            )
            positions = ", ".join(
                profile.get("latest_queries") or profile.get("target_positions") or []
            )
            if positions:
                st.markdown(
                    template(
                        "profile_list_positions.html", positions=html.escape(positions)
                    ),
                    unsafe_allow_html=True,
                )
            if profile.get("summary"):
                st.markdown(
                    template(
                        "profile_list_summary.html",
                        summary=html.escape(short_summary(profile["summary"])),
                    ),
                    unsafe_allow_html=True,
                )
        with action:
            if st.button(
                "Открыть",
                key=f"open_{profile['id']}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["selected_profile_id"] = str(profile["id"])
                st.switch_page("pages/profile.py")
