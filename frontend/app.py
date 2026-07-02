import asyncio
import io

import aiohttp
import pandas as pd
import streamlit as st

API_URL = "http://backend:8080/v1/cv_analyzer/send_cv"

st.set_page_config(
    page_title="Job Hunter",
    page_icon="💼",
    layout="wide",
)


async def send_cv(file_bytes: bytes, filename: str, content_type: str) -> bytes:
    form_data = aiohttp.FormData()
    form_data.add_field(
        name="file",
        value=file_bytes,
        filename=filename,
        content_type=content_type,
    )
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=API_URL,
            data=form_data,
            timeout=aiohttp.ClientTimeout(total=1200),
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"Ошибка сервера {response.status}: {error_text}")
            return await response.read()


st.title("Job Hunter")
st.caption(
    "Загрузите резюме — агент найдёт подходящие вакансии на hh.ru и покажет их здесь."
)

uploaded_file = st.file_uploader(
    label="Резюме",
    type=["pdf", "docx", "doc", "txt"],
    help="Поддерживаются форматы: PDF, DOCX, DOC, TXT",
)

if uploaded_file is not None:
    if st.button("Найти вакансии", type="primary", use_container_width=True):
        with st.status("Анализирую резюме и ищу вакансии…", expanded=True) as status:
            st.write("Отправляю резюме агенту…")

            try:
                csv_bytes = asyncio.run(
                    send_cv(
                        file_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                        content_type=uploaded_file.type,
                    )
                )
            except aiohttp.ClientConnectorError:
                status.update(label="Ошибка соединения", state="error")
                st.error(
                    "Не удалось подключиться к backend. Убедитесь, что сервер запущен."
                )
                st.stop()
            except asyncio.TimeoutError:
                status.update(label="Превышено время ожидания", state="error")
                st.error("Сервер не ответил за 20 минут. Попробуйте позже.")
                st.stop()
            except RuntimeError as exc:
                status.update(label="Ошибка", state="error")
                st.error(str(exc))
                st.stop()

            st.write("Формирую таблицу…")
            status.update(label="Готово!", state="complete")

        dataframe = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8-sig")

        st.success(f"Найдено вакансий: {len(dataframe)}")

        if "link" in dataframe.columns:
            dataframe["link"] = dataframe["link"].apply(
                lambda url: (
                    f'<a href="{url}" target="_blank">открыть</a>'
                    if pd.notna(url)
                    else ""
                )
            )
            st.write(
                dataframe.to_html(escape=False, index=False), unsafe_allow_html=True
            )
        else:
            st.dataframe(dataframe, use_container_width=True)

        st.download_button(
            label="Скачать CSV",
            data=csv_bytes,
            file_name="vacancies.csv",
            mime="text/csv",
        )
