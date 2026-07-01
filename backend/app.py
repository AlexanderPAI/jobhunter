import asyncio
import logging

from langchain_core.messages import HumanMessage

from backend.agents.cv_analyzer.agent import CVAnalyzerAgent
from backend.agents.searcher.agent import Agent as SearcherAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MULTIAGENT")

cv_analyzer_agent = CVAnalyzerAgent()
searcher_agent = SearcherAgent()


async def main():
    searcher_prompt, _ = await cv_analyzer_agent.run("resume.pdf")
    answer, _ = await searcher_agent.run(
        {
            "messages": [HumanMessage(content=searcher_prompt)],
            "greeted": True,
            "waiting_for_user": False,
            "search_queries": [],
            "filters": None,
            "area": 1,
            "max_pages": 3,
            "csv_path": "",
            "final_answer": "",
        }
    )


if __name__ == "__main__":
    loop = asyncio.run(main())
