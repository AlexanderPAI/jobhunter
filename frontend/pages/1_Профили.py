import asyncio
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from frontend.db import get_profiles

MOSCOW = ZoneInfo("Europe/Moscow")

st.set_page_config(page_title="Профили — Job Hunter", page_icon="👤", layout="wide")

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
    .profile-meta { color: #617085; font-size: .86rem; }
    .profile-summary { color: #39465a; line-height: 1.55; margin-top: .55rem; }
    .stButton > button { border-radius: 8px; font-weight: 700; }
    [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.page_link("app.py", label="Новый подбор", icon="📄")
    st.page_link("pages/1_Профили.py", label="Профили", icon="👥")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Подборов ещё не было"
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M")


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
            positions = html.escape(", ".join(profile.get("target_positions") or []))
            meta = " · ".join(
                item
                for item in [
                    positions,
                    html.escape(profile.get("experience_level") or ""),
                    html.escape(profile.get("location") or ""),
                ]
                if item
            )
            st.markdown(
                f'<div class="profile-name">{name}</div>', unsafe_allow_html=True
            )
            if meta:
                st.markdown(
                    f'<div class="profile-meta">{meta}</div>', unsafe_allow_html=True
                )
            if profile.get("summary"):
                st.markdown(
                    f'<div class="profile-summary">{html.escape(profile["summary"])}</div>',
                    unsafe_allow_html=True,
                )
            last_search = format_datetime(profile.get("last_search_at"))
            relevant = profile.get("relevant_count")
            result_note = f" · {relevant} подходящих" if relevant is not None else ""
            st.caption(f"Последний подбор: {last_search}{result_note}")
        with action:
            if st.button(
                "Открыть",
                key=f"open_{profile['id']}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["selected_profile_id"] = str(profile["id"])
                st.switch_page("pages/2_Профиль.py")
