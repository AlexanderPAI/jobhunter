import asyncio
import html
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import pandas as pd
import streamlit as st

from frontend.api import repeat_search
from frontend.db import get_profile, get_search_vacancies

MOSCOW = ZoneInfo("Europe/Moscow")

st.set_page_config(page_title="Профиль — Job Hunter", page_icon="👤", layout="wide")

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 1.6rem; }
    .detail-title { font-size: 2.6rem; font-weight: 800; color: #172033; margin: .4rem 0; }
    .detail-summary { color: #4f5e72; line-height: 1.65; font-size: 1rem; }
    .section-title { color: #2563eb; font-size: .78rem; font-weight: 800;
        letter-spacing: .09em; text-transform: uppercase; margin-bottom: .6rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.94); border-color: #d9e2ef !important;
        box-shadow: 0 12px 28px rgba(37,99,235,.06); border-radius: 10px;
    }
    .stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 700; }
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
        return "—"
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M")


def show_value(label: str, value) -> None:
    if value in (None, "", []):
        return
    st.caption(label)
    if isinstance(value, list):
        st.write(" · ".join(str(item) for item in value))
    else:
        st.write(value)


if st.button("← Все профили"):
    st.switch_page("pages/1_Профили.py")

profile_id = st.session_state.get("selected_profile_id")
if not profile_id:
    st.info("Сначала выберите профиль в списке.")
    st.page_link("pages/1_Профили.py", label="Открыть профили", icon="👥")
    st.stop()

try:
    profile, latest_search = asyncio.run(get_profile(profile_id))
except Exception as exc:
    st.error(f"Не удалось получить профиль из базы данных: {exc}")
    st.stop()

if profile is None:
    st.error("Профиль не найден.")
    st.stop()

st.markdown(
    f'<div class="detail-title">{html.escape(profile.get("name") or "Без имени")}</div>',
    unsafe_allow_html=True,
)
if profile.get("summary"):
    st.markdown(
        f'<div class="detail-summary">{html.escape(profile["summary"])}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Профессиональный профиль</div>',
            unsafe_allow_html=True,
        )
        show_value("Желаемые позиции", profile.get("target_positions"))
        show_value("Навыки", profile.get("skills"))
        show_value("Опыт, лет", profile.get("experience_years"))
        show_value("Уровень", profile.get("experience_level"))
        show_value("Ожидаемая зарплата", profile.get("salary_expectation"))
        show_value("Отрасли", profile.get("industries"))
with right:
    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Предпочтения и сведения</div>',
            unsafe_allow_html=True,
        )
        show_value("Город", profile.get("location"))
        show_value("Формат работы", profile.get("preferred_schedule"))
        show_value("Занятость", profile.get("preferred_employment"))
        show_value("Языки", profile.get("languages"))
        show_value("Образование", profile.get("education"))
        show_value("Исходный файл", profile.get("source_filename"))

st.divider()
header, action = st.columns([4, 1.5], vertical_alignment="bottom")
with header:
    st.subheader("Последний подбор вакансий")
    if latest_search:
        st.caption(
            f"Дата и время: {format_datetime(latest_search.get('created_at'))} · "
            f"найдено {latest_search.get('total_found') or 0} · "
            f"подходящих {latest_search.get('relevant_count') or 0}"
        )
    else:
        st.caption("Для этого профиля вакансии ещё не подбирались.")
with action:
    repeat_disabled = latest_search is None or not latest_search.get("prompt")
    repeat_clicked = st.button(
        "Подобрать вакансии снова",
        type="primary",
        use_container_width=True,
        disabled=repeat_disabled,
    )

if repeat_disabled:
    st.caption(
        "Повторный подбор станет доступен после первого поиска со страницы загрузки резюме."
    )

if repeat_clicked:
    with st.status("Повторный подбор вакансий", expanded=True) as status:
        try:
            st.write("Ищу новые вакансии на hh.ru и Хабр Карьере…")
            asyncio.run(repeat_search(latest_search["prompt"], profile_id))
            st.write("Фильтрация завершена. Обновляю результаты…")
            status.update(label="Новый подбор готов", state="complete")
            st.rerun()
        except aiohttp.ClientConnectorError:
            status.update(label="Backend недоступен", state="error")
            st.error("Не удалось подключиться к backend.")
        except (TimeoutError, RuntimeError) as exc:
            status.update(label="Не удалось выполнить подбор", state="error")
            st.error(str(exc))

if latest_search:
    try:
        vacancies = asyncio.run(
            get_search_vacancies(
                str(latest_search["id"]),
                relevant_only=latest_search.get("filtered_at") is not None,
            )
        )
    except Exception as exc:
        st.error(f"Не удалось получить вакансии из базы данных: {exc}")
        st.stop()

    if vacancies:
        dataframe = pd.DataFrame(vacancies)
        st.dataframe(
            dataframe,
            hide_index=True,
            use_container_width=True,
            column_config={
                "title": "Вакансия",
                "company": "Компания",
                "salary": "Зарплата",
                "city": "Город",
                "schedule": "График",
                "experience": "Опыт",
                "link": st.column_config.LinkColumn("Ссылка", display_text="Открыть ↗"),
                "source": "Источник",
                "query": None,
            },
        )
        st.download_button(
            "Скачать CSV",
            dataframe.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"vacancies_{profile_id}.csv",
            mime="text/csv",
        )
    else:
        st.info("В последнем подборе нет подходящих вакансий.")
