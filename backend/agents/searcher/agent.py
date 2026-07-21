"""
Job Search Agent
======================

Граф:
  greet  →  parse_user_input  →  run_parser  →  done
              ↑___________________________|
              (если пользователь не ответил — ждём)

Диалог:
  1. greet       — агент объясняет что умеет и задаёт вопрос
  2. parse_user_input — LLM разбирает ответ в SearchFilters + список запросов
  3. run_parser  — вызывает tools, сохраняет общую выдачу в PostgreSQL
  4. done        — отвечает пользователю
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.agents.searcher.tools import parse_habr_vacancies, parse_vacancies
from backend.config import cfg
from backend.db.connector import async_session
from backend.db.repositories import save_search
from backend.llm_providers.openrouter import OpenRouterAdapter
from backend.utils.prompt_loader import load_prompt

logger = logging.getLogger("SEARCHER")

# Prompts
greeting_prompt = load_prompt(Path(__file__).parent / "prompts/base.yaml", "greeting")
parse_user_input_system = load_prompt(
    Path(__file__).parent / "prompts/base.yaml", "parse_user_input_system"
)


class State(TypedDict):
    messages: Annotated[List, add_messages]
    greeted: bool
    waiting_for_user: bool
    search_queries: List[str]
    filters: Optional[dict]
    area: int
    max_pages: int
    profile_id: str | None
    user_id: str
    search_id: str
    final_answer: str


class Agent:
    CSV_FIELDS = [
        "title",
        "company",
        "salary",
        "city",
        "schedule",
        "experience",
        "link",
        "query",
    ]

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
            "messages": [AIMessage(content=greeting_prompt)],
        }

    # Роутер после Ноды 1
    def _route_after_greet(self, state: State) -> str:
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                return "parse_user_input"
            if isinstance(message, AIMessage) and message.content == greeting_prompt:
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
            {"role": "system", "content": parse_user_input_system},
            {"role": "user", "content": user_text},
        ]

        response = await self.llm.chat(prompt)
        raw_content = (
            ((response.get("choices") or [{}])[0].get("message") or {}).get("content")
            or ""
        ).strip()

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

    @staticmethod
    def _merge_results(*groups: list[dict]) -> list[dict]:
        rows: list[dict] = []
        seen_links = set()
        for group in groups:
            for row in group:
                link = row.get("link") or ""
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                rows.append(row)
        return rows

    # Нода 3: запукаем тулу парсера
    async def run_parser_node(self, state: State) -> dict:
        parser_payload = {
            "search_queries": state["search_queries"],
            "filters": state.get("filters") or {},
            "area": state.get("area", 1),
            "max_pages": state.get("max_pages", 1),
        }

        hh_result, habr_result = await asyncio.gather(
            parse_vacancies.ainvoke(parser_payload),
            parse_habr_vacancies.ainvoke(parser_payload),
        )
        rows = self._merge_results(hh_result["vacancies"], habr_result["vacancies"])
        original_prompt = next(
            (m.content for m in state["messages"] if isinstance(m, HumanMessage)), ""
        )
        async with async_session() as session:
            search = await save_search(
                session,
                profile_id=state.get("profile_id"),
                user_id=state["user_id"],
                prompt=original_prompt,
                queries=state["search_queries"],
                filters=state.get("filters") or {},
                area=state.get("area", 1),
                max_pages=state.get("max_pages", 1),
                rows=rows,
            )

        return {
            "search_id": str(search.id),
            "messages": [
                AIMessage(
                    content=(
                        f"Парсинг завершён: {len(rows)} вакансий. "
                        f"HH: {hh_result['total_count']}, "
                        f"Habr: {habr_result['total_count']}."
                    )
                )
            ],
        }

    # Нода 4: делаем ответ для пользователя
    async def done(self, state: State) -> dict:
        answer = f"Результат сохранён, поиск {state['search_id']}"
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

    async def run(self, message: str, profile_id: str | None, user_id: str) -> str:
        initial_state: State = {
            "messages": [HumanMessage(content=message)],
            "greeted": True,
            "waiting_for_user": False,
            "search_queries": [],
            "filters": None,
            "area": 1,
            "max_pages": 3,
            "profile_id": profile_id,
            "user_id": user_id,
            "search_id": "",
            "final_answer": "",
        }

        result_state = await self.graph.ainvoke(initial_state)

        search_id = result_state.get("search_id", "")
        if not search_id:
            raise RuntimeError("Parser did not return search_id")
        return search_id


async def _main():
    agent = Agent()
    user_input = input("Вы: ").strip()
    if not user_input:
        return
    search_id = await agent.run(user_input)
    print(f"\nПоиск сохранён: {search_id}")


if __name__ == "__main__":
    asyncio.run(_main())
