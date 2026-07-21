import asyncio

import aiohttp
import streamlit as st

from frontend.api import login


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
    if st.session_state.get("access_token"):
        return
    st.markdown("## Job Hunter")
    st.caption("Войдите, чтобы продолжить")
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
    st.caption(f"Пользователь: {st.session_state.get('username', '—')}")
    if st.button("Выйти", use_container_width=True):
        logout()
        st.switch_page("app.py")
