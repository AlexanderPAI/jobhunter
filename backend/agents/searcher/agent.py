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
  3. run_parser  — вызывает tools, сохраняет общий CSV
  4. done        — отвечает пользователю
"""

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.agents.searcher.tools import parse_habr_vacancies, parse_vacancies
from backend.config import cfg
from backend.models.openrouter import OpenRouterAdapter
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
    csv_path: str
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

    @staticmethod
    def _results_dir() -> Path:
        results_dir = Path(__file__).parent.parent.parent / "storage/results"
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir

    @classmethod
    def _merge_parser_csvs(
        cls, source_paths: list[str | Path], result_path: Path
    ) -> int:
        rows = []
        seen_links = set()

        for source_path in source_paths:
            path = Path(source_path)
            if not path.exists():
                logger.warning(f"CSV file does not exist and will be skipped: {path}")
                continue

            with path.open(newline="", encoding="utf-8-sig") as input_file:
                reader = csv.DictReader(input_file)
                for row in reader:
                    link = row.get("link") or ""
                    if link in seen_links:
                        continue
                    seen_links.add(link)
                    rows.append({field: row.get(field, "") for field in cls.CSV_FIELDS})

        with result_path.open("w", newline="", encoding="utf-8-sig") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=cls.CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        return len(rows)

    # Нода 3: запукаем тулу парсера
    async def run_parser_node(self, state: State) -> dict:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = self._results_dir()
        hh_csv_path = results_dir / f"hh_vacancies_{timestamp}.csv"
        habr_csv_path = results_dir / f"habr_vacancies_{timestamp}.csv"
        result_csv_path = results_dir / f"vacancies_{timestamp}.csv"

        parser_payload = {
            "search_queries": state["search_queries"],
            "filters": state.get("filters") or {},
            "area": state.get("area", 1),
            "max_pages": state.get("max_pages", 1),
        }

        hh_result, habr_result = await asyncio.gather(
            parse_vacancies.ainvoke(
                {
                    **parser_payload,
                    "csv_path": str(hh_csv_path),
                }
            ),
            parse_habr_vacancies.ainvoke(
                {
                    **parser_payload,
                    "csv_path": str(habr_csv_path),
                }
            ),
        )

        total_count = self._merge_parser_csvs(
            [hh_result["csv_path"], habr_result["csv_path"]],
            result_csv_path,
        )

        return {
            "csv_path": str(result_csv_path),
            "messages": [
                AIMessage(
                    content=(
                        f"Парсинг завершён: {total_count} вакансий. "
                        f"HH: {hh_result['total_count']}, "
                        f"Habr: {habr_result['total_count']}. "
                        f"Файл: {result_csv_path}"
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

    async def run(self, message: str) -> str:
        initial_state: State = {
            "messages": [HumanMessage(content=message)],
            "greeted": True,
            "waiting_for_user": False,
            "search_queries": [],
            "filters": None,
            "area": 1,
            "max_pages": 3,
            "csv_path": "",
            "final_answer": "",
        }

        result_state = await self.graph.ainvoke(initial_state)

        csv_path = result_state.get("csv_path", "")
        if not csv_path:
            raise RuntimeError("Parser did not return csv_path")

        if not Path(csv_path).exists():
            raise RuntimeError(f"CSV file does not exist: {csv_path}")

        return csv_path


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
