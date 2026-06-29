import asyncio
import csv
import json
import logging
import re

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PARSER")


SEARCH_QUERIES = [
    "AI разработчик",
    "AI Product Lead",
    "ML engineer",
    "LLM разработчик",
    "AI инженер",
]

AREA = 1  # 1 = Москва; 0 = вся Россия
MAX_PAGES = 3  # страниц на каждый запрос (50 вакансий / страница)
RESULTS_JSON = "hh_vacancies.json"
RESULTS_CSV = "hh_vacancies.csv"


class HHParser:

    def __init__(
        self,
        search_queries: list[str],
        area: int,
        max_pages: int,
        save_to_json: bool = False,
        save_to_csv: bool = False,
    ) -> None:
        self.search_queries = search_queries
        self.area = area
        self.max_pages = max_pages
        self.results_json_path = RESULTS_JSON
        self.results_csv_path = RESULTS_CSV
        self.save_to_json = save_to_json
        self.save_to_csv = save_to_csv
        self.results = []

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _salary_from_card(card) -> str:
        """
        Ищет зарплату в карточке: сначала через data-qa-compensation,
        потом через любой элемент с «₽» в тексте.
        """
        # Вариант 1: data-qa содержит "compensation-frequency"
        # sal_qa = card.query_selector_all('[data-qa*="compensation-frequency"]')
        # Это теги-метки ("два раза в месяц"), а сама сумма — их родительский контейнер
        # Поэтому берём весь compensation-блок через класс compensation-labels
        # Вариант 2: просто ищем текст с «₽»
        return None  # Playwright — async, обрабатываем ниже

    async def _get_salary(self, card) -> str:
        """Async-вариант: проходит по всем span/div карточки в поисках ₽."""
        # Сначала ищем явный data-qa
        sal_els = await card.query_selector_all(
            '[data-qa*="vacancy-serp__vacancy-compensation"]'
        )
        for el in sal_els:
            t = self._clean(await el.inner_text())
            if t and "₽" in t:  # только элементы с реальной суммой
                return t

        # Запасной вариант — любой элемент с ₽ и длиной < 80
        all_els = await card.query_selector_all("span, div")
        for el in all_els:
            t = self._clean(await el.inner_text())
            if "₽" in t and len(t) < 80:
                # Убираем мусор ("Выплаты: два раза в месяц")
                amount = re.sub(
                    r"(Выплаты.*|Опыт.*|на руки|на счёт)", "", t, flags=re.I
                )
                amount = self._clean(amount)
                if amount:
                    return amount
        return "не указана"

    async def _get_schedule(self, card) -> str:
        """Формат: удалёнка / гибрид / офис."""
        remote = await card.query_selector(
            '[data-qa="vacancy-label-work-schedule-remote"]'
        )
        if remote:
            return self._clean(await remote.inner_text())
        return "—"

    async def _get_experience(self, card) -> str:
        """Требуемый опыт."""
        exp = await card.query_selector(
            '[data-qa*="vacancy-serp__vacancy-work-experience"]'
        )
        if exp:
            return self._clean(await exp.inner_text())
        return "—"

    async def parse_page(self, page) -> list[dict]:
        """Парсит все карточки с текущей страницы выдачи."""
        await page.wait_for_selector(
            '[data-qa="vacancy-serp__vacancy"]', timeout=15_000
        )
        cards = await page.query_selector_all('[data-qa="vacancy-serp__vacancy"]')

        for card in cards:
            try:
                # Название + ссылка
                title_el = await card.query_selector('[data-qa="serp-item__title"]')
                title = self._clean(await title_el.inner_text()) if title_el else "—"
                href = await title_el.get_attribute("href") if title_el else None
                link = href.split("?")[0] if href else "—"  # чистый URL без трекинга

                # Компания
                company_el = await card.query_selector(
                    '[data-qa="vacancy-serp__vacancy-employer"]'
                )
                company = (
                    self._clean(await company_el.inner_text()) if company_el else "—"
                )

                # Зарплата
                salary = await self._get_salary(card)

                # Город
                city_el = await card.query_selector(
                    '[data-qa="vacancy-serp__vacancy-address"]'
                )
                city = self._clean(await city_el.inner_text()) if city_el else "—"

                # Формат работы и опыт
                schedule = await self._get_schedule(card)
                experience = await self._get_experience(card)

                self.results.append(
                    {
                        "title": title,
                        "company": company,
                        "salary": salary,
                        "city": city,
                        "schedule": schedule,
                        "experience": experience,
                        "link": link,
                    }
                )
            except Exception as exc:
                logger.error(f"    [!] Ошибка при разборе карточки: {exc}")

        return self.results

    async def search(self, browser, query: str) -> list[dict]:
        """Ищет вакансии по одному запросу, обходит MAX_PAGES страниц."""
        ctx = await browser.new_context(
            locale="ru-RU",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()
        all_results: list[dict] = []

        try:
            for page_num in range(self.max_pages):
                url = (
                    f"https://hh.ru/search/vacancy"
                    f"?text={query.replace(' ', '+')}"
                    f"&area={AREA}"
                    f"&page={page_num}"
                    f"&per_page=20"
                )
                logger.info(f"  ↳ стр. {page_num + 1}: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await page.wait_for_timeout(1_200)

                # Проверяем пустую выдачу
                content = await page.content()
                if "Ничего не найдено" in content:
                    logger.info("    [!] Нет результатов — стоп")
                    break

                # Ждём карточки (если нет — стоп)
                try:
                    await page.wait_for_selector(
                        '[data-qa="vacancy-serp__vacancy"]', timeout=8_000
                    )
                except Exception:
                    logger.info("    [!] Карточки не появились — стоп")
                    break

                page_vacancies = await self.parse_page(page)
                if not page_vacancies:
                    break

                for v in page_vacancies:
                    v["query"] = query
                all_results.extend(page_vacancies)
                logger.info(f"    ✓ найдено: {len(page_vacancies)}")

                # Следующая страница?
                next_btn = await page.query_selector('[data-qa="pager-next"]')
                if not next_btn:
                    break

                await page.wait_for_timeout(600)

        finally:
            await ctx.close()

        return all_results

    def save_json(self, data: list[dict]) -> None:
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✓ {RESULTS_JSON}  ({len(data)} записей)")

    def save_csv(self, data: list[dict]) -> None:
        if not data:
            return
        fields = [
            "title",
            "company",
            "salary",
            "city",
            "schedule",
            "experience",
            "link",
            "query",
        ]
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
        logger.info(f"  ✓ {RESULTS_CSV}")

    def deduplicate(self, data: list[dict]) -> list[dict]:
        seen, unique = set(), []
        for v in data:
            if v["link"] not in seen:
                seen.add(v["link"])
                unique.append(v)
        return unique

    async def run_parser(self):
        logger.info("=" * 60)
        logger.info("  hh.ru Parser  ")
        logger.info(f"  Запросы: {', '.join(self.search_queries)}")
        logger.info(
            f"  Регион: {'Москва' if AREA == 1 else 'Вся Россия'}  |  Страниц: {self.max_pages}"
        )
        logger.info("=" * 60)

        all_vacancies: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            for query in self.search_queries:
                logger.info(f"[→] «{query}»")
                results = await self.search(browser, query)
                all_vacancies.extend(results)
                logger.info(f"    Итого: {len(results)}")
                await asyncio.sleep(1.5)

            await browser.close()

        unique = self.deduplicate(all_vacancies)
        logger.info(f"\n{'─' * 60}")
        logger.info(f"Уникальных вакансий: {len(unique)}")
        logger.info(f"{'─' * 60}")

        logger.info("\nСохранение:")
        if self.save_to_json:
            self.save_json(unique)
        if self.save_csv:
            self.save_csv(unique)

        # Превью
        logger.info(f"\n{'─' * 60}")
        logger.info("Топ-10 результатов:")
        logger.info(f"{'─' * 60}")
        for v in unique[:10]:
            logger.info(f"  {v['title']}")
            logger.info(f"    {v['company']}  |  {v['city']}  |  {v['salary']}")
            if v["experience"] != "—":
                logger.info(f"    {v['experience']}  |  {v['schedule']}")
            logger.info(f"    {v['link']}")


# async def main():
#     parser = Parser(
#         search_queries=SEARCH_QUERIES,
#         area=AREA,
#         max_pages=MAX_PAGES,
#         save_to_csv=True,
#     )
#     await parser.run_parser()
#
# if __name__ == "__main__":
#     asyncio.run(main())
