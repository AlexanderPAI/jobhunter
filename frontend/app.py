import asyncio
import io

import aiohttp
import pandas as pd
import streamlit as st

CV_ANALYZER_URL = "http://backend:8080/v1/cv_analyzer/send_cv"
SEARCHER_URL = "http://backend:8080/v1/searcher/chat"
FILTER_URL = "http://backend:8080/v1/filter/check"

st.set_page_config(page_title="Job Hunter", page_icon="💼", layout="wide")

CSS = """
<style>
.block-container { padding-top: 1.8rem; padding-bottom: 1.5rem; max-width: 1200px; }
h1 { font-size: 1.4rem !important; font-weight: 700 !important;
color: #e2e8f0 !important; margin-bottom: 0.1rem !important; }

.cards-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    margin-top: 1.2rem;
    margin-bottom: 1.2rem;
}
.card {
    background: #0f172a;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    box-sizing: border-box;
}
.card-title {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #38bdf8;
    margin-bottom: 0.7rem;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 0.4rem;
}
.card-body { font-size: 0.82rem; color: #cbd5e1; line-height: 1.6; }

.profile-row { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.3rem; flex-wrap: wrap; }
.profile-key { color: #7dd3fc; font-size: 0.75rem; flex-shrink: 0; white-space: nowrap; }
.profile-key::after { content: ":"; margin-right: 2px; }
.profile-val { color: #e2e8f0; font-size: 0.75rem; }
.tag {
    display: inline-block;
    background: #1e3a5f;
    border: 1px solid #2563eb44;
    border-radius: 4px;
    padding: 1px 7px;
    font-size: 0.7rem;
    color: #93c5fd;
    margin: 2px 3px 2px 0;
}

.vacancy-table-wrap {
    overflow-y: auto;
    overflow-x: hidden;
    max-height: 440px;
    border-radius: 8px;
    border: 1px solid #1e3a5f;
    background: #0f172a;
}
.vacancy-table-wrap table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
    color: #cbd5e1;
    table-layout: fixed;
}
.vacancy-table-wrap th {
    background: #0a0f1e;
    color: #38bdf8;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    padding: 8px 12px;
    text-align: left;
    position: sticky;
    top: 0;
    z-index: 1;
    border-bottom: 1px solid #1e3a5f;
}
.vacancy-table-wrap td { padding: 7px 12px; border-top: 1px solid #162032;
vertical-align: top; word-break: break-word; }
.vacancy-table-wrap tr:hover td { background: #162032; }
.vacancy-table-wrap a { color: #60a5fa; text-decoration: none; }
.vacancy-table-wrap a:hover { color: #93c5fd; text-decoration: underline; }

/* скрываем встроенные кнопки Deploy / Stop */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
</style>
"""

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


async def call_cv_analyzer(file_bytes, filename, content_type):
    form_data = aiohttp.FormData()
    form_data.add_field(
        "file", file_bytes, filename=filename, content_type=content_type
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            CV_ANALYZER_URL, data=form_data, timeout=aiohttp.ClientTimeout(total=1200)
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ошибка сервера {resp.status}: {await resp.text()}")
            return await resp.json()


async def call_searcher(search_prompt: str) -> str:
    """Возвращает путь к CSV на сервере."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            SEARCHER_URL,
            json={"message": search_prompt},
            timeout=aiohttp.ClientTimeout(total=1200),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ошибка сервера {resp.status}: {await resp.text()}")
            data = await resp.json()
            return data["result_path"]


async def call_filter(csv_path: str, user_profile: dict) -> bytes:
    """Отправляет путь к CSV и профиль, получает отфильтрованный CSV."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            FILTER_URL,
            json={"csv_path": csv_path, "user_profile": user_profile},
            timeout=aiohttp.ClientTimeout(total=1200),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ошибка сервера {resp.status}: {await resp.text()}")
            return await resp.read()


def render_profile_card(profile):
    rows = ""
    for key, label in PROFILE_LABELS.items():
        value = profile.get(key)
        if not value:
            continue
        if isinstance(value, list):
            tags = "".join(f'<span class="tag">{item}</span>' for item in value)
            rows += (
                f'<div class="profile-row"><span class="profile-key">{label}</span>'
                f'<span class="profile-val">{tags}</span></div>'
            )
        else:
            rows += (
                f'<div class="profile-row"><span class="profile-key">{label}</span>'
                f'<span class="profile-val">{value}</span></div>'
            )
    return f'<div class="card"><div class="card-title">Профиль</div><div class="card-body">{rows}</div></div>'


def render_text_card(title, text):
    return f'<div class="card"><div class="card-title">{title}</div><div class="card-body">{text}</div></div>'


def render_vacancy_table(dataframe):
    visible = [col for col in COL_META if col in dataframe.columns]
    header = "".join(
        f'<th style="width:{COL_META[col][1]}">{COL_META[col][0]}</th>'
        for col in visible
    )
    rows = ""
    for _, row in dataframe[visible].iterrows():
        cells = ""
        for col in visible:
            val = row[col]
            if col == "link" and pd.notna(val):
                cells += f'<td><a href="{val}" target="_blank">открыть ↗</a></td>'
            else:
                cells += f"<td>{val if pd.notna(val) else '—'}</td>"
        rows += f"<tr>{cells}</tr>"
    return f'<div class="vacancy-table-wrap"><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown(CSS, unsafe_allow_html=True)
st.title("💼 Job Hunter")
st.caption("Загрузите резюме — агент проанализирует его и подберёт вакансии на hh.ru.")

uploaded_file = st.file_uploader(
    label="Загрузите резюме",
    type=["pdf", "docx", "doc", "txt"],
    help="PDF, DOCX, DOC, TXT",
    label_visibility="collapsed",
)

if uploaded_file is not None:
    if st.button("Анализировать резюме", type="primary", use_container_width=True):
        with st.spinner("Анализирую резюме…"):
            try:
                api_response = asyncio.run(
                    call_cv_analyzer(
                        uploaded_file.getvalue(), uploaded_file.name, uploaded_file.type
                    )
                )
                st.session_state["api_response"] = api_response
                st.session_state["csv_bytes"] = None
            except aiohttp.ClientConnectorError:
                st.error("Не удалось подключиться к backend.")
                st.stop()
            except asyncio.TimeoutError:
                st.error("Сервер не ответил за 20 минут.")
                st.stop()
            except RuntimeError as exc:
                st.error(str(exc))
                st.stop()

if "api_response" in st.session_state:
    api_response = st.session_state["api_response"]
    profile = api_response.get("user_profile", {})
    summary = profile.get("summary", "—")
    search_prompt = api_response.get("search_prompt", "—")

    st.markdown(
        f'<div class="cards-row">'
        f"{render_profile_card(profile)}"
        f'{render_text_card("Краткое описание", summary)}'
        f'{render_text_card("Запрос для поиска вакансий", search_prompt)}'
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("Подобрать вакансии", type="primary", use_container_width=True):
        with st.status("Ищу вакансии на hh.ru…", expanded=True) as search_status:
            try:
                st.write("Парсю hh.ru…")
                csv_path = asyncio.run(call_searcher(search_prompt))

                search_status.update(
                    label="Проверяю и фильтрую полученный список вакансий…"
                )
                st.write("Фильтрую нерелевантные вакансии…")
                csv_bytes = asyncio.run(call_filter(csv_path, profile))

                search_status.update(label="Готово!", state="complete")
                st.session_state["csv_bytes"] = csv_bytes
            except aiohttp.ClientConnectorError:
                search_status.update(label="Ошибка соединения", state="error")
                st.error("Не удалось подключиться к backend.")
                st.stop()
            except asyncio.TimeoutError:
                search_status.update(label="Превышено время ожидания", state="error")
                st.error("Сервер не ответил за 20 минут.")
                st.stop()
            except RuntimeError as exc:
                search_status.update(label="Ошибка", state="error")
                st.error(str(exc))
                st.stop()

if st.session_state.get("csv_bytes"):
    csv_bytes = st.session_state["csv_bytes"]
    dataframe = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8-sig")
    with st.expander(f"Вакансии — {len(dataframe)} результатов", expanded=True):
        st.markdown(render_vacancy_table(dataframe), unsafe_allow_html=True)
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.download_button(
            label="Скачать CSV",
            data=csv_bytes,
            file_name="vacancies.csv",
            mime="text/csv",
        )
