import json
import logging

import zendriver as zd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Letterboxd:
    base_url = "https://letterboxd.com"

    def __init__(self, cache):
        self.cache = cache

    # Film id is json that needs to be parsed
    def _parse_film_id(self, film_id_str):
        film_id_json = json.loads(film_id_str)
        uid = film_id_json.get("uid")
        film_id = int(uid.replace("film:", ""))

        return film_id

    # Parse item url eg /film/despicable-me-4/
    async def _parse_item(self, url, retry_count=3, timeout=30):
        logger.debug(f"Parse url {url} with retry")

        browser = await zd.start(headless=False, no_sandbox=True)

        page = await browser.get(url)

        for n in range(retry_count):
            try:
                await page.select("body.film", timeout=timeout)

                response = await page.get_content()

                await browser.stop()

                return response
            except TimeoutError as err:
                logger.error(f"Error waiting for page to load: {err}")

                if n == retry_count - 1:
                    raise err

    # Parse list url eg /jdemeza/watchlist/by/release/
    # Parse id and slug of each item eg 448506, despicable-me-4
    async def _parse_items(self, list_url, retry_count=3, timeout=30):
        items = []
        page_number = 1

        browser = await zd.start(headless=False, no_sandbox=True)

        page = await browser.get(list_url)

        while True:
            logger.debug(f"Get page {page_number} of {list_url}")

            for n in range(retry_count):
                try:
                    logger.debug(f"Parse url {list_url} with retry")

                    # Wait for page to load
                    await page.select(".poster-grid, .poster-list", timeout=timeout)

                    response = await page.get_content()

                    soup = BeautifulSoup(response, "lxml")

                    # Restrict to main column, avoid 'cloned from'
                    section = soup.find("section", {"class": "col-main"})

                    divs = section.find_all("div", {"data-postered-identifier": True})

                    for div in divs:
                        film_id = self._parse_film_id(div["data-postered-identifier"])
                        film_slug = div["data-item-slug"]
                        logger.debug(f"Found slug {film_slug} for id {film_id}")
                        items.append((film_id, film_slug))

                    next_button = await page.query_selector("a.next")

                    if next_button:
                        page_number += 1

                        await next_button.click()
                    else:
                        await browser.stop()

                        return items
                except TimeoutError as err:
                    logger.error(f"Error waiting for page to load: {err}")

                    if n == retry_count - 1:
                        raise err

    # Get TMDB ids from a Letterboxd list
    async def get_tmdb_ids(self, list_url):
        tmdb_ids = {}

        try:
            items = await self._parse_items(f"{self.base_url}{list_url}")

            for item in items:
                film_id, film_slug = item

                # Check cache first
                tmdb_id, letterboxd_id = self.cache.query_id_map_by_letterboxd(film_id)

                if tmdb_id is None:
                    response = await self._parse_item(
                        f"{self.base_url}/film/{film_slug}"
                    )

                    soup = BeautifulSoup(response, "lxml")
                    body = soup.find("body")

                    str_tmdb_id = body.get("data-tmdb-id")

                    if not str_tmdb_id:
                        logger.debug(
                            f"Could not find tmdb id for Letterboxd id {film_id}"
                        )
                        continue

                    tmdb_id = int(str_tmdb_id)
                    self.cache.add_id_map(tmdb_id, film_id, None)
                    logger.debug(
                        f"Found tmdb id {tmdb_id} for Letterboxd id {film_id}, added to cache"
                    )
                else:
                    logger.debug(
                        f"Found tmdb id {tmdb_id} for Letterboxd id {film_id} in cache"
                    )

                tmdb_ids[tmdb_id] = film_id
        except Exception as err:
            logger.error(f"Unable to parse Letterboxd list, exception: {err}")
            tmdb_ids = None

        return tmdb_ids
