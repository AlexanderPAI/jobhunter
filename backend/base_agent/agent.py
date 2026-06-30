"""
HH.ru Job Search Agent
Flow: analyze_queries → run_parser → save_and_respond
"""

import asyncio
import json
import logging
import re
from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.base_agent.tools import parse_vacancies
from backend.config import cfg
from backend.models.openrouter import OpenRouterAdapter


class State(TypedDict):
    messages: Annotated[List, add_messages]
    user_queries: List[str]  # исходный список от пользователя
    expanded_queries: List[str]  # расширенный список после LLM-анализа
    csv_path: str  # куда сохранён результат
    final_answer: str  # ответ пользователю


logger = logging.getLogger("AGENT")


class Agent:
    def __init__(self) -> None:
        self.llm = OpenRouterAdapter(
            openrouter_url="https://openrouter.ai/api/v1/chat/completions",
            openrouter_key=cfg.openrouter_key,
            model="z-ai/glm-5.2",
        )
        self.graph = self._build_graph()

    # Нода 1: анализ и дополнение списка запросов
    async def analyze_queries_node(self, state: State) -> dict:
        """
        LLM принимает список вакансий от пользователя и добавляет
        похожие/смежные наименования.
        """
        logger.info("Анализирую и дополняю список, представленный пользователем...")
        user_queries = state["user_queries"]

        prompt = [
            {
                "role": "system",
                "content": (
                    "Ты — ассистент по поиску работы. "
                    "Пользователь передаёт список названий вакансий. "
                    "Твоя задача — расширить этот список похожими и смежными наименованиями, "
                    "которые также могут встречаться на hh.ru. "
                    "Верни ТОЛЬКО JSON-массив строк без пояснений. "
                    "Включи оригинальные запросы и добавь новые. "
                    "Не дублируй. Максимум 5 итоговых запросов."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(user_queries, ensure_ascii=False),
            },
        ]

        response = await self.llm.chat(prompt)
        raw = response["choices"][0]["message"]["content"].strip()

        # Парсим JSON-массив из ответа LLM
        try:
            # Ищем первый JSON-массив в ответе
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            expanded = json.loads(match.group()) if match else user_queries
        except (json.JSONDecodeError, AttributeError):
            # Если LLM вернул не JSON — используем исходный список
            expanded = user_queries

        # Дедупликация без изменения порядка
        seen = set()
        unique_expanded = []
        for q in expanded:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_expanded.append(q)
        logger.info("Анализ и дополнение списка завершено...")
        return {
            "expanded_queries": unique_expanded,
            "messages": [
                AIMessage(content=f"Расширенный список запросов: {unique_expanded}")
            ],
        }

    # Нода 2: запуск парсера через tool
    async def run_parser_node(self, state: State) -> dict:
        """
        Вызывает tool parse_vacancies с расширенным списком запросов.
        """
        logger.info("Вызываю инструмент поиска вакансий...")
        queries = state["expanded_queries"]

        result = await parse_vacancies.ainvoke(
            {
                "search_queries": queries,
                "area": 1,  # Москва; при необходимости вынести в State
                "max_pages": 3,
            }
        )
        logger.info("Поиск вакансий завершен")
        return {
            "csv_path": result["csv_path"],
            "messages": [
                AIMessage(
                    content=(
                        f"Парсинг завершён. "
                        f"Найдено {result['total_count']} вакансий. "
                        f"Файл: {result['csv_path']}"
                    )
                )
            ],
        }

    async def save_and_respond_node(self, state: State) -> dict:
        """
        Формирует финальное сообщение пользователю.
        """
        logger.info("Сохраняю результат и формирую ответ пользователю...")
        csv_path = state["csv_path"]
        final_answer = f"Результат сохранен в {csv_path}"
        logger.info(f"Задача выполнена. Результат сохранен в {csv_path}")
        return {
            "final_answer": final_answer,
            "messages": [AIMessage(content=final_answer)],
        }

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(State)

        workflow.add_node("analyze_queries", self.analyze_queries_node)
        workflow.add_node("run_parser", self.run_parser_node)
        workflow.add_node("save_and_respond", self.save_and_respond_node)

        workflow.set_entry_point("analyze_queries")
        workflow.add_edge("analyze_queries", "run_parser")
        workflow.add_edge("run_parser", "save_and_respond")
        workflow.add_edge("save_and_respond", END)

        return workflow.compile()

    async def chat(self, user_message: str) -> str:
        """
        user_message — строка с перечнем вакансий, одна на строку
        или через запятую.
        Возвращает финальное сообщение агента.
        """
        # Парсим ввод пользователя в список
        raw_queries = [
            q.strip() for q in re.split(r"[\n,;]+", user_message) if q.strip()
        ]

        initial_state: State = {
            "messages": [HumanMessage(content=user_message)],
            "user_queries": raw_queries,
            "expanded_queries": [],
            "csv_path": "",
            "final_answer": "",
        }

        final_state = await self.graph.ainvoke(initial_state)
        return final_state["final_answer"]


if __name__ == "__main__":
    agent = Agent()

    user_input = input("Введите список вакансий (через запятую или по строкам):\n> ")
    result = asyncio.run(agent.chat(user_input))
    print(result)
