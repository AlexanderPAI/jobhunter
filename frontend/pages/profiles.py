import asyncio
import html

import streamlit as st

from frontend.api import get_profiles
from frontend.auth import render_account_sidebar, require_auth

st.set_page_config(page_title="Профили — Job Hunter", page_icon="👤", layout="wide")
require_auth()

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .profiles-title { font-size: 2.6rem; font-weight: 800; color: #172033; margin: 0; }
    .profiles-lead { color: #617085; margin: .5rem 0 1.5rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.94); border-color: #d9e2ef !important;
        box-shadow: 0 12px 28px rgba(37,99,235,.06); border-radius: 10px;
    }
    .profile-name { font-size: 1.25rem; font-weight: 800; color: #172033; }
    .profile-positions { color: #2563eb; font-size: .88rem; font-weight: 650; margin-top: .25rem; }
    .profile-summary { color: #39465a; font-size: .88rem; line-height: 1.55; margin: .55rem 0 .4rem; }
    .stButton > button { border-radius: 8px; font-weight: 700; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    render_account_sidebar()
    st.page_link("app.py", label="Новый подбор", icon="📄")
    st.page_link("pages/profiles.py", label="Профили", icon="👥")


def short_summary(value: str | None) -> str:
    words = (value or "").split()
    summary = " ".join(words[:20])
    return f"{summary}…" if len(words) > 20 else summary


st.markdown(
    '<div class="profiles-title">Профили кандидатов</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="profiles-lead">Сохранённые профили и результаты последних подборов вакансий.</div>',
    unsafe_allow_html=True,
)

try:
    profiles = asyncio.run(get_profiles())
except Exception as exc:
    st.error(f"Не удалось получить профили из базы данных: {exc}")
    st.stop()

if not profiles:
    st.info("Профилей пока нет. Загрузите резюме на странице подбора вакансий.")
    st.page_link("app.py", label="Перейти к загрузке резюме", icon="📄")
    st.stop()

for profile in profiles:
    with st.container(border=True):
        main, action = st.columns([5, 1.2], vertical_alignment="center")
        with main:
            name = html.escape(profile.get("name") or "Без имени")
            positions = html.escape(
                ", ".join(
                    profile.get("latest_queries")
                    or profile.get("target_positions")
                    or []
                )
            )
            st.markdown(
                f'<div class="profile-name">{name}</div>', unsafe_allow_html=True
            )
            if positions:
                st.markdown(
                    f'<div class="profile-positions">{positions}</div>',
                    unsafe_allow_html=True,
                )
            if profile.get("summary"):
                st.markdown(
                    f'<div class="profile-summary">{html.escape(short_summary(profile["summary"]))}</div>',
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
