"""
HH.ru Vacancy Filter Agent
===========================

Граф:
  load_data  ->  filter_vacancies  ->  save_result  ->  END

Флоу:
  1. load_data        -- читает CSV с вакансиями и профиль пользователя
  2. filter_vacancies -- LLM анализирует названия вакансий батчами
                         и решает, релевантна ли каждая профилю
  3. save_result      -- сохраняет отфильтрованный CSV через tool

Агент не трогает содержимое вакансий -- только фильтрует строки по
полю title на основе профиля кандидата.
"""

import asyncio
import csv
import json
import logging
import re
from pathlib import Path
from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.agents.vacancy_filter.tools import save_filtered_csv
from backend.config import cfg
from backend.models.openrouter import OpenRouterAdapter
from backend.utils.prompt_loader import load_prompt

logger = logging.getLogger("VACANCY_FILTER")

filter_system_prompt = load_prompt(
    Path(__file__).parent / "prompts/base.yaml", "filter_system"
)

# Сколько названий вакансий отправляем LLM за один запрос.
BATCH_SIZE = 30

# ---- State ------------------------------------------------------------------


class State(TypedDict):
    messages: Annotated[List, add_messages]
    csv_path: str
    user_profile: dict
    all_rows: list[dict]
    filtered_rows: list[dict]
    output_csv_path: str


# ---- Agent ------------------------------------------------------------------


class VacancyFilterAgent:
    def __init__(self) -> None:
        self.llm = OpenRouterAdapter(
            openrouter_url="https://openrouter.ai/api/v1/chat/completions",
            openrouter_key=cfg.openrouter_key,
            model="z-ai/glm-5.2",
        )
        self.graph = self._build_graph()

    # Нода 1: загружаем CSV
    async def load_data(self, state: State) -> dict:
        with open(state["csv_path"], encoding="utf-8-sig") as csv_file:
            all_rows = list(csv.DictReader(csv_file))

        logger.info(f"Загружено {len(all_rows)} вакансий из {state['csv_path']}")

        return {
            "all_rows": all_rows,
            "messages": [AIMessage(content=f"Загружено {len(all_rows)} вакансий.")],
        }

    # Нода 2: фильтруем батчами
    async def filter_vacancies(self, state: State) -> dict:
        all_rows = state["all_rows"]
        profile = state["user_profile"]
        profile_json = json.dumps(profile, ensure_ascii=False)

        # Уникальные названия (порядок сохранён)
        titles = [row.get("title", "") for row in all_rows]
        unique_titles = list(dict.fromkeys(titles))
        logger.info(f"Уникальных названий: {len(unique_titles)}, батч: {BATCH_SIZE}")

        relevant_titles: set[str] = set()

        for batch_start in range(0, len(unique_titles), BATCH_SIZE):
            # fmt: off
            batch = unique_titles[batch_start: batch_start + BATCH_SIZE]
            numbered = "\n".join(
                f"{idx + 1}. {title}" for idx, title in enumerate(batch)
            )
            # fmt: on

            prompt = [
                {"role": "system", "content": filter_system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Профиль кандидата:\n{profile_json}\n\n"
                        f"Список названий вакансий:\n{numbered}"
                    ),
                },
            ]

            response = await self.llm.chat(prompt)

            raw_content = (
                (response.get("choices") or [{}])[0].get("message", {}).get("content")
            )

            try:
                match = re.search(r"\[.*?\]", raw_content, re.DOTALL)
                relevant_indices = json.loads(match.group()) if match else []
            except (json.JSONDecodeError, AttributeError):
                relevant_indices = []

            for idx in relevant_indices:
                if isinstance(idx, int) and 1 <= idx <= len(batch):
                    relevant_titles.add(batch[idx - 1])

            logger.info(
                f"Батч {batch_start // BATCH_SIZE + 1}: "
                f"{len(batch)} -> {len(relevant_indices)} релевантных"
            )

        filtered_rows = [
            row for row in all_rows if row.get("title", "") in relevant_titles
        ]
        logger.info(f"Итого: {len(filtered_rows)} / {len(all_rows)}")

        return {
            "filtered_rows": filtered_rows,
            "messages": [
                AIMessage(
                    content=(
                        f"Фильтрация завершена: "
                        f"{len(filtered_rows)} из {len(all_rows)} вакансий релевантны."
                    )
                )
            ],
        }

    # Нода 3: сохраняем через tool
    async def save_result(self, state: State) -> dict:
        source_path = Path(state["csv_path"])
        output_path = str(
            source_path.parent / f"{source_path.stem}_filtered{source_path.suffix}"
        )

        save_filtered_csv.invoke(
            {"rows": state["filtered_rows"], "output_path": output_path}
        )

        return {
            "output_csv_path": output_path,
            "messages": [AIMessage(content=f"Результат сохранён в {output_path}")],
        }

    # Сборка графа
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(State)

        workflow.add_node("load_data", self.load_data)
        workflow.add_node("filter_vacancies", self.filter_vacancies)
        workflow.add_node("save_result", self.save_result)

        workflow.set_entry_point("load_data")
        workflow.add_edge("load_data", "filter_vacancies")
        workflow.add_edge("filter_vacancies", "save_result")
        workflow.add_edge("save_result", END)

        return workflow.compile()

    async def run(self, csv_path: str, user_profile: dict) -> tuple[str, State]:
        """
        Args:
            csv_path    : путь к CSV от searcher-а
            user_profile: профиль кандидата от cv_analyzer-а

        Returns:
            (путь к отфильтрованному CSV, итоговый state)
        """
        initial_state: State = {
            "messages": [],
            "csv_path": csv_path,
            "user_profile": user_profile,
            "all_rows": [],
            "filtered_rows": [],
            "output_csv_path": "",
        }

        result_state = await self.graph.ainvoke(initial_state)
        return result_state.get("output_csv_path", ""), result_state


# ---- CLI --------------------------------------------------------------------


async def _main():
    import sys

    if len(sys.argv) < 3:
        print("Использование: python vacancy_filter_agent.py <csv_path> <profile.json>")
        return

    with open(sys.argv[2], encoding="utf-8") as profile_file:
        user_profile = json.load(profile_file)

    agent = VacancyFilterAgent()
    output_path, _ = await agent.run(sys.argv[1], user_profile)
    print(f"\nОтфильтрованный CSV: {output_path}")


if __name__ == "__main__":
    asyncio.run(_main())
