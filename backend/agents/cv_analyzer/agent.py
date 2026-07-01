"""
HH.ru CV Analyzer Agent
=======================

Граф:
  extract_cv  →  build_profile  →  generate_searcher_prompt  →  run_searcher  →  done

Флоу:
  1. extract_cv               — читает файл резюме в текст
  2. build_profile            — LLM строит структурированный профиль пользователя
  3. generate_searcher_prompt — LLM генерирует входной промпт для agent-searcher
  4. run_searcher             — передаёт промпт в Agent-searcher (parse_user_input → run_parser → done)
  5. done                     — возвращает итоговый ответ пользователю
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Annotated, List, TypedDict

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.agents.cv_analyzer.tools import extract_cv_text
from backend.config import cfg
from backend.models.openrouter import OpenRouterAdapter
from backend.utils.prompt_loader import load_prompt

logger = logging.getLogger("CV_ANALYZER")

# Prompts
build_profile_system = load_prompt(
    Path(__file__).parent / "prompts/base.yaml", "build_profile_system"
)
generate_searcher_prompt_system = load_prompt(
    Path(__file__).parent / "prompts/base.yaml", "generate_searcher_prompt_system"
)


# State
class State(TypedDict):
    messages: Annotated[List, add_messages]
    cv_path: str
    cv_text: str
    user_profile: dict
    final_answer: str


class CVAnalyzerAgent:
    def __init__(self):
        self.llm = OpenRouterAdapter(
            openrouter_url="https://openrouter.ai/api/v1/chat/completions",
            openrouter_key=cfg.openrouter_key,
            model="z-ai/glm-5.2",
        )
        self.graph = self._build_graph()

    # Нода 1: читаем файл резюме
    async def extract_cv(self, state: State) -> dict:
        cv_text = extract_cv_text.invoke({"cv_path": state["cv_path"]})
        logger.info(f"Читаю резюме {state['cv_path']}")
        logger.info(f"Длина текста CV: {len(cv_text)}")

        return {
            "cv_text": cv_text,
            "messages": [
                AIMessage(content=f"Резюме прочитано ({len(cv_text)} символов).")
            ],
        }

    # Нода 2: создаем профиль пользователя
    async def build_profile(self, state: State) -> dict:
        logger.info("Создаю профиль пользователя")
        prompt = [
            {"role": "system", "content": build_profile_system},
            {"role": "user", "content": state["cv_text"]},
        ]

        response = await self.llm.chat(prompt)
        raw_content = response["choices"][0]["message"]["content"].strip()

        try:
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            user_profile = json.loads(json_match.group()) if json_match else {}
        except (json.JSONDecodeError, AttributeError):
            user_profile = {}

        logger.info("Профиль построен:")
        for key, value in user_profile.items():
            logger.info(f"{key}: {value}")

        return {
            "user_profile": user_profile,
            "messages": [AIMessage(content="Профиль кандидата составлен.")],
        }

    # Нода 3: генерируем промпт для agent-searcher
    async def generate_searcher_prompt(self, state: State) -> dict:
        profile_json = json.dumps(state["user_profile"], ensure_ascii=False, indent=2)

        prompt = [
            {"role": "system", "content": generate_searcher_prompt_system},
            {"role": "user", "content": profile_json},
        ]

        response = await self.llm.chat(prompt)
        final_answer = response["choices"][0]["message"]["content"].strip()

        logger.info(f"Промпт для searcher-а: {final_answer[:120]}...")

        return {
            "final_answer": final_answer,
            "messages": [AIMessage(content=final_answer)],
        }

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(State)

        workflow.add_node("extract_cv", self.extract_cv)
        workflow.add_node("build_profile", self.build_profile)
        workflow.add_node("generate_searcher_prompt", self.generate_searcher_prompt)

        workflow.set_entry_point("extract_cv")
        workflow.add_edge("extract_cv", "build_profile")
        workflow.add_edge("build_profile", "generate_searcher_prompt")
        workflow.add_edge("generate_searcher_prompt", END)

        return workflow.compile()

    async def run(self, cv_path: str) -> tuple[str, State]:
        """
        Args:
            cv_path: путь к файлу резюме (.txt, .pdf, .docx)

        Returns:
            (searcher_prompt, итоговый state)
        """
        initial_state: State = {
            "messages": [],
            "cv_path": cv_path,
            "cv_text": "",
            "user_profile": {},
            "searcher_prompt": "",
        }

        result_state = await self.graph.ainvoke(initial_state)
        return result_state.get("final_answer", ""), result_state


async def _main():
    cv_agent = CVAnalyzerAgent()
    final_answer, _ = await cv_agent.run("resume.doc")
    with open("final_answer.txt", "w") as f:
        f.write(final_answer)


if __name__ == "__main__":
    asyncio.run(_main())
