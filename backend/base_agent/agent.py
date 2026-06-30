"""
HH.ru Job Search Agent
======================

Граф:
  greet  →  parse_user_input  →  run_parser  →  done
              ↑___________________________|
              (если пользователь не ответил — ждём)

Диалог:
  1. greet       — агент объясняет что умеет и задаёт вопрос
  2. parse_user_input — LLM разбирает ответ в SearchFilters + список запросов
  3. run_parser  — вызывает tool, сохраняет CSV
  4. done        — отвечает пользователю
"""

import asyncio
import json
import logging
import re
from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.base_agent.tools import parse_vacancies
from backend.config import cfg
from backend.models.openrouter import OpenRouterAdapter

logger = logging.getLogger("AGENT")

# Приветствие
# todo hard-code
GREETING = """\
Привет! Я помогу найти вакансии на hh.ru и сохранить результат в CSV.

Расскажи, что ищешь. Можно указать:

  • Названия вакансий — одно или несколько (я добавлю похожие сам)
    Пример: «Python backend, FastAPI разработчик»

  • Регион — «Москва» (по умолчанию) или «вся Россия»

  • Зарплата — «от 150 000» / «до 300 000» / «от 150 до 300»

  • Только с указанной ЗП — «только с зарплатой»

  • График — удалёнка / полный день / гибкий / сменный / вахта

  • Опыт — без опыта / 1–3 года / 3–6 лет / более 6 лет

  • Занятость — полная / частичная / проектная / стажировка

  • Сортировка — по убыванию ЗП / по возрастанию ЗП / по дате

  • Исключить компании — «без Яндекса, без HeadHunter»

  • Обязательные слова в названии — «обязательно AI»

  • Исключить слова в названии — «без стажёр, без junior»

Можно писать в свободной форме — я разберу сам.\
"""

# Prompts
# todo перенести в yaml

PARSE_USER_INPUT_SYSTEM = """\
Ты — ассистент по поиску работы. Пользователь описал, какую работу ищет.

Твоя задача — вернуть ТОЛЬКО валидный JSON без каких-либо пояснений.

Структура JSON:
{
  "search_queries": [...],   // список запросов: оригинальные + похожие (max 12)
  "area": 1,                 // 1 = Москва (по умолчанию), 0 = вся Россия
  "max_pages": 3,            // страниц на запрос (по умолчанию 3)
  "filters": {
    "salary_from": null,          // int | null
    "only_with_salary": false,    // bool
    "schedule": [],               // список из: "remote","fullDay","flexible","shift","flyInFlyOut"
    "experience": [],             // список из: "noExperience","between1And3","between3And6","moreThan6"
    "employment": [],             // список из: "full","part","project","volunteer","probation"
    "order_by": "relevance",      // "relevance"|"salary_desc"|"salary_asc"|"name"|"publication_time"
    "search_field": "",           // "" | "name"
    "salary_to": null,            // int | null
    "exclude_companies": [],
    "require_keywords": [],
    "exclude_keywords": []
  }
}

Правила:
- Расширяй search_queries синонимами и смежными наименованиями.
- schedule, experience, employment — ТОЛЬКО из допустимых значений выше.
- «удалёнка» → schedule: ["remote"]
- «без junior/стажёр» → exclude_keywords: ["junior","стажёр"]
- «только с зарплатой» → only_with_salary: true
- «вся Россия» → area: 0
- Не добавляй комментарии в JSON, верни только объект.\
"""


class State(TypedDict):
    messages: Annotated[List, add_messages]
    greeted: bool
    waiting_for_user: bool
    search_queries: List[str]
    filters: Optional[dict]
    area: int
    max_pages: int
    csv_path: str
    final_answer: str


class Agent:
    def __init__(self) -> None:
        self.llm = OpenRouterAdapter(
            openrouter_url="https://openrouter.ai/api/v1/chat/completions",
            openrouter_key=cfg.openrouter_key,
            model="z-ai/glm-5.2",
        )
        self.graph = self._build_graph()

    # Нода 1: приветствие
    async def greet(self, state: State) -> dict:
        return {
            "greeted": True,
            "waiting_for_user": True,
            "messages": [AIMessage(content=GREETING)],
        }

    # Роутер после Ноды 1
    def _route_after_greet(self, state: State) -> str:
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                return "parse_user_input"
            if isinstance(message, AIMessage) and message.content == GREETING:
                return END
        return END

    # Нода 2: разбираем, что указал пользователь

    async def parse_user_input(self, state: State) -> dict:
        user_text = ""
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                user_text = message.content
                break

        prompt = [
            {"role": "system", "content": PARSE_USER_INPUT_SYSTEM},
            {"role": "user", "content": user_text},
        ]

        response = await self.llm.chat(prompt)
        raw_content = response["choices"][0]["message"]["content"].strip()

        try:
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            parsed = json.loads(json_match.group()) if json_match else {}
        except (json.JSONDecodeError, AttributeError):
            parsed = {}

        search_queries = parsed.get("search_queries") or [user_text[:80]]
        area = parsed.get("area", 1)
        max_pages = parsed.get("max_pages", 3)
        filters = parsed.get("filters", {})

        return {
            "search_queries": search_queries,
            "area": area,
            "max_pages": max_pages,
            "filters": filters,
            "waiting_for_user": False,
            "messages": [
                AIMessage(content=f"Запускаю поиск по {len(search_queries)} запросам…")
            ],
        }

    # Нода 3: запукаем тулу парсера
    async def run_parser_node(self, state: State) -> dict:
        tool_result = await parse_vacancies.ainvoke(
            {
                "search_queries": state["search_queries"],
                "filters": state.get("filters") or {},
                "area": state.get("area", 1),
                "max_pages": state.get("max_pages", 3),
                "csv_path": "",
            }
        )

        return {
            "csv_path": tool_result["csv_path"],
            "messages": [
                AIMessage(
                    content=(
                        f"Парсинг завершён: {tool_result['total_count']} вакансий. "
                        f"Файл: {tool_result['csv_path']}"
                    )
                )
            ],
        }

    # Нода 4: делаем ответ для пользователя
    async def done(self, state: State) -> dict:
        answer = f"Результат сохранён в {state['csv_path']}"
        return {
            "final_answer": answer,
            "messages": [AIMessage(content=answer)],
        }

    # Сборка графа
    def _route_entry(self, state: State) -> str:
        """Точка входа: если приветствие уже было — сразу к разбору запроса."""
        if state["greeted"]:
            return "parse_user_input"
        return "greet"

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(State)

        workflow.add_node("greet", self.greet)
        workflow.add_node("parse_user_input", self.parse_user_input)
        workflow.add_node("run_parser", self.run_parser_node)
        workflow.add_node("done", self.done)

        workflow.set_entry_point("router")
        workflow.add_node("router", lambda state: state)
        workflow.add_conditional_edges(
            "router",
            self._route_entry,
            {
                "greet": "greet",
                "parse_user_input": "parse_user_input",
            },
        )

        workflow.add_conditional_edges(
            "greet",
            self._route_after_greet,
            {
                "parse_user_input": "parse_user_input",
                END: END,
            },
        )

        workflow.add_edge("parse_user_input", "run_parser")
        workflow.add_edge("run_parser", "done")
        workflow.add_edge("done", END)

        return workflow.compile()

    async def run(self, state: State) -> tuple[str, State]:
        """
        Единственная точка входа.
        - Первый вызов: state["greeted"] = False → граф отправит приветствие и остановится.
        - Второй вызов: state["greeted"] = True + HumanMessage в messages → граф выполнит поиск.

        Returns:
            (текст последнего AIMessage, обновлённый state)
        """
        result_state = await self.graph.ainvoke(state)
        last_message = next(
            (
                msg
                for msg in reversed(result_state["messages"])
                if isinstance(msg, AIMessage)
            ),
            None,
        )
        return (last_message.content if last_message else ""), result_state


async def _main():
    agent = Agent()

    initial_state: State = {
        "messages": [],
        "greeted": False,
        "waiting_for_user": False,
        "search_queries": [],
        "filters": None,
        "area": 1,
        "max_pages": 3,
        "csv_path": "",
        "final_answer": "",
    }

    greeting, after_greet_state = await agent.run(initial_state)
    print(f"\nАгент:\n{greeting}\n")

    user_input = input("Вы: ").strip()
    if not user_input:
        return

    after_greet_state["messages"] = list(after_greet_state["messages"]) + [
        HumanMessage(content=user_input)
    ]
    after_greet_state["greeted"] = True

    answer, _ = await agent.run(after_greet_state)
    print(f"\nАгент: {answer}")


if __name__ == "__main__":
    asyncio.run(_main())
