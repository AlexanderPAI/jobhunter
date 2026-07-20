import asyncio

import aiohttp
import pandas as pd
import streamlit as st

CV_ANALYZER_URL = "http://backend:8080/v1/cv_analyzer/send_cv"
SEARCHER_URL = "http://backend:8080/v1/searcher/chat"
FILTER_URL = "http://backend:8080/v1/filter/check"

st.set_page_config(page_title="Job Hunter", page_icon="💼", layout="wide")

CSS = """
<style>
:root {
    --jh-bg: #f5f8fc;
    --jh-surface: #ffffff;
    --jh-surface-soft: #edf4fb;
    --jh-ink: #172033;
    --jh-muted: #617085;
    --jh-line: #d9e2ef;
    --jh-primary: #2563eb;
    --jh-primary-strong: #1d4ed8;
    --jh-primary-soft: #dbeafe;
    --jh-accent: #0f9f8f;
    --jh-accent-soft: #dff7f2;
    --jh-shadow: 0 18px 45px rgba(37, 99, 235, 0.08);
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(219, 234, 254, 0.9), transparent 32rem),
        linear-gradient(180deg, #fbfdff 0%, var(--jh-bg) 46%, #eef6fb 100%);
    color: var(--jh-ink);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1180px;
}

.jh-header {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    gap: 1rem;
    margin-bottom: 1.4rem;
}

.jh-eyebrow {
    color: var(--jh-primary);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

.jh-title {
    color: var(--jh-ink);
    font-size: clamp(2rem, 4vw, 3.4rem);
    font-weight: 800;
    line-height: 0.95;
    margin: 0;
}

.jh-lead {
    color: var(--jh-muted);
    font-size: 1rem;
    line-height: 1.55;
    max-width: 680px;
    margin-top: 0.8rem;
}

.jh-badge {
    background: var(--jh-accent-soft);
    border: 1px solid #b8ece4;
    border-radius: 999px;
    color: #087568;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0.55rem 0.8rem;
    white-space: nowrap;
}

.cards-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    margin-top: 1.25rem;
    margin-bottom: 1.25rem;
}

.card {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid var(--jh-line);
    border-radius: 8px;
    padding: 1rem 1.05rem;
    box-sizing: border-box;
    box-shadow: 0 12px 28px rgba(37, 99, 235, 0.06);
    min-height: 100%;
}

.card-title {
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--jh-primary);
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--jh-line);
    padding-bottom: 0.48rem;
}

.card-body { font-size: 0.86rem; color: var(--jh-muted); line-height: 1.58; }

.profile-row {
    display: flex;
    align-items: baseline;
    gap: 0.42rem;
    margin-bottom: 0.42rem;
    flex-wrap: wrap;
}

.profile-key {
    color: var(--jh-primary);
    font-size: 0.76rem;
    font-weight: 750;
    flex-shrink: 0;
    white-space: nowrap;
}

.profile-key::after { content: ":"; margin-right: 2px; }

.profile-val { color: var(--jh-ink); font-size: 0.78rem; }

.tag {
    display: inline-block;
    background: var(--jh-primary-soft);
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 0.72rem;
    color: var(--jh-primary-strong);
    margin: 2px 4px 2px 0;
    font-weight: 650;
}

.vacancy-table-wrap {
    overflow-y: auto;
    overflow-x: hidden;
    max-height: 560px;
    border-radius: 8px;
    border: 1px solid var(--jh-line);
    background: var(--jh-surface);
    box-shadow: var(--jh-shadow);
}

.vacancy-table-wrap table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
    color: var(--jh-ink);
    table-layout: fixed;
}

.vacancy-table-wrap th {
    background: #edf4fb;
    color: var(--jh-primary);
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 10px 12px;
    text-align: left;
    position: sticky;
    top: 0;
    z-index: 1;
    border-bottom: 1px solid var(--jh-line);
    font-weight: 800;
}

.vacancy-table-wrap td {
    padding: 9px 12px;
    border-top: 1px solid #edf2f8;
    vertical-align: top;
    word-break: break-word;
}

.vacancy-table-wrap tr:nth-child(even) td { background: #fbfdff; }
.vacancy-table-wrap tr:hover td { background: #eef7ff; }
.vacancy-table-wrap a { color: var(--jh-primary); text-decoration: none; font-weight: 700; }
.vacancy-table-wrap a:hover { color: var(--jh-accent); text-decoration: underline; }

.stButton > button,
.stDownloadButton > button {
    border-radius: 8px !important;
    min-height: 2.7rem;
    font-weight: 750 !important;
    border: 1px solid rgba(37, 99, 235, 0.22) !important;
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.15);
}

.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
.stDownloadButton > button {
    background: var(--jh-primary) !important;
    color: white !important;
}

.stButton > button:hover,
[data-testid="stBaseButton-primary"]:hover,
.stDownloadButton > button:hover {
    border-color: var(--jh-accent) !important;
    box-shadow: 0 12px 24px rgba(15, 159, 143, 0.16);
}

[data-testid="stFileUploader"] {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid var(--jh-line);
    border-radius: 8px;
    padding: 0.8rem 0.95rem;
    box-shadow: 0 12px 28px rgba(37, 99, 235, 0.05);
}

[data-testid="stFileUploaderDropzone"] {
    background: var(--jh-surface-soft) !important;
    border: 1px dashed #93c5fd !important;
    border-radius: 8px !important;
}

[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p {
    color: var(--jh-muted) !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--jh-line) !important;
    border-radius: 8px !important;
    background: rgba(255, 255, 255, 0.72) !important;
    box-shadow: 0 12px 28px rgba(37, 99, 235, 0.05);
}

[data-testid="stStatus"] {
    border-radius: 8px !important;
    border-color: var(--jh-line) !important;
}

.stAlert {
    border-radius: 8px;
}

@media (max-width: 900px) {
    .jh-header { grid-template-columns: 1fr; }
    .jh-badge { justify-self: start; }
    .cards-row { grid-template-columns: 1fr; }
}

/* скрываем встроенные кнопки Deploy / Stop */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
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


async def call_searcher(search_prompt: str, profile_id: str) -> str:
    """Возвращает идентификатор сохранённого поиска."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            SEARCHER_URL,
            json={"message": search_prompt, "profile_id": profile_id},
            timeout=aiohttp.ClientTimeout(total=1200),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ошибка сервера {resp.status}: {await resp.text()}")
            data = await resp.json()
            return data["search_id"]


async def call_filter(search_id: str) -> list[dict]:
    """Фильтрует сохранённый поиск и возвращает вакансии."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            FILTER_URL,
            json={"search_id": search_id},
            timeout=aiohttp.ClientTimeout(total=1200),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Ошибка сервера {resp.status}: {await resp.text()}")
            return (await resp.json())["vacancies"]


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

with st.sidebar:
    st.page_link("app.py", label="Новый подбор", icon="📄")
    st.page_link("pages/profiles.py", label="Профили", icon="👥")

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    """
    <div class="jh-header">
        <div>
            <div class="jh-eyebrow">Job Hunter</div>
            <h1 class="jh-title">Поиск вакансий без лишнего шума</h1>
            <div class="jh-lead">
                Загрузите резюме — агент соберёт профиль, найдёт вакансии на hh.ru
                и Хабр Карьере, а затем отфильтрует список под ваш опыт.
            </div>
        </div>
        <div class="jh-badge">CSV на выходе</div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
                st.session_state["vacancies"] = None
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
    profile_id = api_response.get("profile_id")

    st.markdown(
        f'<div class="cards-row">'
        f"{render_profile_card(profile)}"
        f'{render_text_card("Краткое описание", summary)}'
        f'{render_text_card("Запрос для поиска вакансий", search_prompt)}'
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("Подобрать вакансии", type="primary", use_container_width=True):
        with st.status("Статус", expanded=True) as search_status:
            status_text = st.empty()
            try:
                status_text.write("Ищу вакансии на hh.ru и Хабр Карьере…")
                search_id = asyncio.run(call_searcher(search_prompt, profile_id))

                status_text.write("Проверяю и фильтрую полученный список вакансий…")
                vacancies = asyncio.run(call_filter(search_id))

                status_text.write("Готово! Подходящие вакансии собраны.")
                search_status.update(label="Статус", state="complete")
                st.session_state["vacancies"] = vacancies
            except aiohttp.ClientConnectorError:
                status_text.write("Ошибка соединения.")
                search_status.update(label="Статус", state="error")
                st.error("Не удалось подключиться к backend.")
                st.stop()
            except asyncio.TimeoutError:
                status_text.write("Превышено время ожидания.")
                search_status.update(label="Статус", state="error")
                st.error("Сервер не ответил за 20 минут.")
                st.stop()
            except RuntimeError as exc:
                status_text.write("Ошибка при подборе вакансий.")
                search_status.update(label="Статус", state="error")
                st.error(str(exc))
                st.stop()

if st.session_state.get("vacancies") is not None:
    dataframe = pd.DataFrame(st.session_state["vacancies"])
    with st.expander(f"Вакансии — {len(dataframe)} результатов", expanded=True):
        st.markdown(render_vacancy_table(dataframe), unsafe_allow_html=True)
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.download_button(
            label="Скачать CSV",
            data=dataframe.to_csv(index=False).encode("utf-8-sig"),
            file_name="vacancies.csv",
            mime="text/csv",
        )
