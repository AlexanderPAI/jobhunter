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

PROFILE_LABELS = {
    "name": "Имя",
    "target_positions": "Позиции",
    "skills": "Навыки",
    "experience_years": "Опыт (лет)",
    "experience_level": "Уровень",
    "salary_expectation": "Ожидаемая ЗП",
    "preferred_schedule": "График",
    "preferred_employment": "Занятость",
    "location": "Город",
    "industries": "Отрасли",
    "languages": "Языки",
    "education": "Образование",
}

COL_META = {
    "title": ("Вакансия", "28%"),
    "company": ("Компания", "18%"),
    "salary": ("Зарплата", "13%"),
    "city": ("Город", "10%"),
    "schedule": ("График", "10%"),
    "experience": ("Опыт", "11%"),
    "link": ("Ссылка", "10%"),
}

st.set_page_config(page_title="Профиль — Job Hunter", page_icon="👤", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --jh-surface: #fff; --jh-ink: #172033; --jh-muted: #617085;
        --jh-line: #d9e2ef; --jh-primary: #2563eb;
        --jh-primary-strong: #1d4ed8; --jh-primary-soft: #dbeafe;
    }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 2rem; }
    .jh-header { display: grid; grid-template-columns: minmax(0,1fr) auto;
        align-items: end; gap: 1rem; margin-bottom: 1.4rem; }
    .jh-eyebrow { color: var(--jh-primary); font-size: .72rem; font-weight: 800;
        letter-spacing: .11em; text-transform: uppercase; margin-bottom: .3rem; }
    .jh-title { color: var(--jh-ink); font-size: clamp(2rem,4vw,3.4rem);
        font-weight: 800; line-height: .95; margin: 0; }
    .jh-lead { color: var(--jh-muted); font-size: 1rem; line-height: 1.55;
        max-width: 680px; margin-top: .8rem; }
    .jh-badge { background: #dff7f2; border: 1px solid #b8ece4;
        border-radius: 999px; color: #087568; font-size: .78rem; font-weight: 700;
        padding: .55rem .8rem; white-space: nowrap; }
    .cards-row { display: grid; grid-template-columns: 1fr; gap: 14px;
        margin: 1.25rem 0; }
    .card { background: rgba(255,255,255,.92); border: 1px solid var(--jh-line);
        border-radius: 8px; padding: 1rem 1.05rem; box-sizing: border-box;
        box-shadow: 0 12px 28px rgba(37,99,235,.06); }
    .card-title { font-size: .7rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: .09em; color: var(--jh-primary); margin-bottom: .75rem;
        border-bottom: 1px solid var(--jh-line); padding-bottom: .48rem; }
    .card-body { font-size: .86rem; color: var(--jh-muted); line-height: 1.58; }
    .profile-row { display: flex; align-items: baseline; gap: .42rem;
        margin-bottom: .42rem; flex-wrap: wrap; }
    .profile-key { color: var(--jh-primary); font-size: .76rem;
        font-weight: 750; flex-shrink: 0; white-space: nowrap; }
    .profile-key::after { content: ":"; margin-right: 2px; }
    .profile-val { color: var(--jh-ink); font-size: .78rem; }
    .tag { display: inline-block; background: var(--jh-primary-soft);
        border: 1px solid #bfdbfe; border-radius: 999px; padding: 2px 8px;
        font-size: .72rem; color: var(--jh-primary-strong); margin: 2px 4px 2px 0;
        font-weight: 650; }
    .vacancy-table-wrap { overflow-y: auto; overflow-x: hidden; max-height: 560px;
        border-radius: 8px; border: 1px solid var(--jh-line); background: #fff; }
    .vacancy-table-wrap table { width: 100%; border-collapse: collapse;
        font-size: .8rem; color: var(--jh-ink); table-layout: fixed; }
    .vacancy-table-wrap th { background: #edf4fb; color: var(--jh-primary);
        font-size: .68rem; text-transform: uppercase; letter-spacing: .08em;
        padding: 10px 12px; text-align: left; position: sticky; top: 0;
        border-bottom: 1px solid var(--jh-line); font-weight: 800; }
    .vacancy-table-wrap td { padding: 9px 12px; border-top: 1px solid #edf2f8;
        vertical-align: top; word-break: break-word; }
    .vacancy-table-wrap tr:nth-child(even) td { background: #fbfdff; }
    .vacancy-table-wrap a { color: var(--jh-primary); text-decoration: none; font-weight: 700; }
    .stButton > button, .stDownloadButton > button { border-radius: 8px !important;
        min-height: 2.7rem; font-weight: 750 !important; }
    [data-testid="stExpander"] { border: 1px solid var(--jh-line) !important;
        border-radius: 8px !important; background: rgba(255,255,255,.72) !important; }
    [data-testid="stSidebarNav"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
    @media (max-width: 900px) { .jh-header { grid-template-columns: 1fr; }
        .jh-badge { justify-self: start; } }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.page_link("app.py", label="Новый подбор", icon="📄")
    st.page_link("pages/profiles.py", label="Профили", icon="👥")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M")


def render_profile_card(profile: dict) -> str:
    rows = ""
    for key, label in PROFILE_LABELS.items():
        value = profile.get(key)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            rendered = "".join(
                f'<span class="tag">{html.escape(str(item))}</span>' for item in value
            )
        else:
            rendered = html.escape(str(value))
        rows += (
            f'<div class="profile-row"><span class="profile-key">{label}</span>'
            f'<span class="profile-val">{rendered}</span></div>'
        )
    return (
        '<div class="card"><div class="card-title">Профиль</div>'
        f'<div class="card-body">{rows}</div></div>'
    )


def render_text_card(title: str, text: str) -> str:
    return (
        f'<div class="card"><div class="card-title">{html.escape(title)}</div>'
        f'<div class="card-body">{html.escape(text or "—")}</div></div>'
    )


def render_vacancy_table(dataframe: pd.DataFrame) -> str:
    visible = [column for column in COL_META if column in dataframe.columns]
    header = "".join(
        f'<th style="width:{COL_META[column][1]}">{COL_META[column][0]}</th>'
        for column in visible
    )
    rows = ""
    for _, row in dataframe[visible].iterrows():
        cells = ""
        for column in visible:
            value = row[column]
            rendered = "—" if pd.isna(value) else html.escape(str(value))
            if column == "link" and pd.notna(value):
                rendered = f'<a href="{html.escape(str(value), quote=True)}" target="_blank">открыть ↗</a>'
            cells += f"<td>{rendered}</td>"
        rows += f"<tr>{cells}</tr>"
    return (
        '<div class="vacancy-table-wrap"><table><thead><tr>'
        f"{header}</tr></thead><tbody>{rows}</tbody></table></div>"
    )


if st.button("← Все профили"):
    st.switch_page("pages/profiles.py")

profile_id = st.session_state.get("selected_profile_id")
if not profile_id:
    st.info("Сначала выберите профиль в списке.")
    st.page_link("pages/profiles.py", label="Открыть профили", icon="👥")
    st.stop()

try:
    profile, latest_search = asyncio.run(get_profile(profile_id))
except Exception as exc:
    st.error(f"Не удалось получить профиль из базы данных: {exc}")
    st.stop()

if profile is None:
    st.error("Профиль не найден.")
    st.stop()

last_search_at = (
    format_datetime(latest_search.get("created_at"))
    if latest_search
    else "Подборов ещё не было"
)
st.markdown(
    f"""
    <div class="jh-header">
        <div>
            <div class="jh-eyebrow">Профиль кандидата</div>
            <h1 class="jh-title">{html.escape(profile.get("name") or "Без имени")}</h1>
            <div class="jh-lead">Последний подбор вакансий: {last_search_at}</div>
        </div>
        <div class="jh-badge">Сохранённый профиль</div>
    </div>
    """,
    unsafe_allow_html=True,
)

search_prompt = latest_search.get("prompt") if latest_search else ""
st.markdown(
    '<div class="cards-row">'
    f"{render_profile_card(profile)}"
    f'{render_text_card("Краткое описание", profile.get("summary") or "—")}'
    f'{render_text_card("Запрос для поиска вакансий", search_prompt or "Поиск ещё не выполнялся")}'
    "</div>",
    unsafe_allow_html=True,
)

repeat_disabled = not latest_search or not search_prompt
if st.button(
    "Подобрать вакансии снова",
    type="primary",
    use_container_width=True,
    disabled=repeat_disabled,
):
    with st.status("Повторный подбор вакансий", expanded=True) as status:
        try:
            st.write("Ищу новые вакансии на hh.ru и Хабр Карьере…")
            asyncio.run(repeat_search(search_prompt, profile_id))
            status.update(label="Новый подбор готов", state="complete")
            st.rerun()
        except aiohttp.ClientConnectorError:
            status.update(label="Backend недоступен", state="error")
            st.error("Не удалось подключиться к backend.")
        except (TimeoutError, RuntimeError) as exc:
            status.update(label="Не удалось выполнить подбор", state="error")
            st.error(str(exc))

if repeat_disabled:
    st.caption("Повторный подбор станет доступен после первого поиска.")

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

    dataframe = pd.DataFrame(vacancies)
    with st.expander(f"Вакансии — {len(dataframe)} результатов", expanded=True):
        if dataframe.empty:
            st.info("В последнем подборе нет подходящих вакансий.")
        else:
            st.markdown(render_vacancy_table(dataframe), unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
            st.download_button(
                "Скачать CSV",
                dataframe.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"vacancies_{profile_id}.csv",
                mime="text/csv",
            )
