import asyncio

import aiohttp
import streamlit as st

from frontend.api import login
from frontend.ui import inject_theme, radar_art, render_brand, template


def logout() -> None:
    for key in (
        "access_token",
        "username",
        "api_response",
        "vacancies",
        "selected_profile_id",
    ):
        st.session_state.pop(key, None)


def require_auth() -> None:
    inject_theme()
    if st.session_state.get("access_token"):
        return
    left, right = st.columns([1.35, 1], vertical_alignment="center")
    with left:
        render_brand()
        st.markdown(template("login_intro.html"), unsafe_allow_html=True)
    with right:
        st.markdown(radar_art(), unsafe_allow_html=True)
    st.markdown("### Вход в КарьеРадар")
    with st.form("login_form"):
        username = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button(
            "Войти", type="primary", use_container_width=True
        )
    if submitted:
        try:
            result = asyncio.run(login(username.strip().lower(), password))
            st.session_state["access_token"] = result["access_token"]
            st.session_state["username"] = result["username"]
            st.rerun()
        except (RuntimeError, aiohttp.ClientError):
            st.error("Неверный логин или пароль либо сервер временно недоступен")
    st.stop()


def render_account_sidebar() -> None:
    st.caption("ЛИЧНЫЙ РАДАР")
    st.markdown(f"**{st.session_state.get('username', '—')}**")
    if st.button("Выйти", use_container_width=True):
        logout()
        st.switch_page("app.py")
