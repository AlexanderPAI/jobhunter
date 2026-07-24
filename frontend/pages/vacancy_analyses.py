import asyncio
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from frontend.api import get_vacancy_analyses
from frontend.auth import render_account_sidebar, require_auth
from frontend.ui import inject_theme, render_brand

MOSCOW = ZoneInfo("Europe/Moscow")

st.set_page_config(
    page_title="Анализы вакансий — КарьеРадар",
    page_icon="🟣",
    layout="wide",
)
require_auth()
inject_theme()

with st.sidebar:
    render_brand()
    render_account_sidebar()
    st.page_link("app.py", label="Новый радар")
    st.page_link("pages/profiles.py", label="Карьерные профили")
    st.page_link("pages/vacancy_analyses.py", label="Анализы вакансий")

st.markdown(
    """
    <div class="kr-eyebrow">История решений</div>
    <h1 class="kr-title kr-title-section">Анализы вакансий</h1>
    <div class="kr-lead kr-section-lead">
        Сохранённые сопоставления карьерных профилей с конкретными вакансиями.
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    analyses = asyncio.run(get_vacancy_analyses())
except Exception as error:
    st.error(f"Не удалось получить историю анализов: {error}")
    st.stop()

if not analyses:
    st.info(
        "Анализов пока нет. Откройте профиль и проверьте соответствие одной "
        "из подобранных вакансий."
    )
    st.page_link("pages/profiles.py", label="Открыть карьерные профили")
    st.stop()

for analysis in analyses:
    created_at: datetime = analysis["created_at"]
    date_label = created_at.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M")
    with st.container(border=True):
        main, meta, action = st.columns([4.5, 1.4, 1.3], vertical_alignment="center")
        with main:
            st.markdown(
                f'<div class="analysis-list-title">'
                f'{html.escape(analysis["vacancy_title"])}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f'{analysis["company"]} · {analysis["source"].upper()}')
        with meta:
            st.caption("Проверено")
            st.markdown(f"**{date_label}**")
        with action:
            if st.button(
                "Открыть",
                key=f"analysis_{analysis['id']}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["selected_analysis_id"] = str(analysis["id"])
                st.switch_page("pages/vacancy_analysis.py")
