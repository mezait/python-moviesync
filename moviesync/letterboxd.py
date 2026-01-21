import logging

import zendriver as zd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Letterboxd:
    base_url = "https://letterboxd.com"

    def __init__(self, cache):
        self.cache = cache

    # Parse list url eg /jdemeza/watchlist/by/release/
    # Parse id and slug of each item eg 448506, despicable-me-4
    async def _parse_items(self, list_url):
        items = []

        logger.debug(f"Parse url {list_url}")

        browser = await zd.start(headless=False, no_sandbox=True)

        i = 1

        page = await browser.get(list_url)

        while True:
            logger.debug(f"Get page {i} of {list_url}")

            # Wait for page to load
            await page.select(".poster-grid")

            response = await page.get_content()

            soup = BeautifulSoup(response, "lxml")

            # Restrict to main column, avoid 'cloned from'
            section = soup.find("section", {"class": "col-main"})

            divs = section.find_all("div", {"data-film-id": True})

            for div in divs:
                film_id = int(div["data-film-id"])
                film_slug = div["data-item-slug"]
                logger.debug(f"Found slug {film_slug} for id {film_id}")
                items.append((film_id, film_slug))

            next_button = await page.query_selector("a.next")

            if next_button:
                i += 1

                await next_button.click()
            else:
                break

        await browser.stop()

        return items

    async def _parse_url(self, url, wait_element):
        logger.debug(f"Parse url {url}")

        browser = await zd.start(headless=False, no_sandbox=True)

        page = await browser.get(url)

        try:
            await page.select(wait_element)
        except Exception as err:
            logger.error(f"Error waiting for page to load: {err}")

        response = await page.get_content()

        await browser.stop()

        return response

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
                    response = await self._parse_url(
                        f"{self.base_url}/film/{film_slug}", "body.film"
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
