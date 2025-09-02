import logging
import requests
import time
from bs4 import BeautifulSoup
from http import HTTPStatus
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class Letterboxd:
    base_url = "https://letterboxd.com"
    
    def __init__(self, cache):
        self.cache = cache

    # Parse id and slug of each item eg 448506, despicable-me-4
    def _parse_items(self, list_url):
        items = []
        
        response = self._withRetry(list_url)        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Next page
        next_url = soup.find("a", { "class": "next" })
        if next_url:
            next_url = next_url.get("href")
        else:
            next_url = ""
    
        divs = soup.find_all("div", { "data-film-id": True })
            
        for div in divs:
            film_id = int(div["data-film-id"])
            film_slug = div["data-item-slug"]
            logger.debug(f"Found slug {film_slug} for id {film_id}")
            items.append((film_id, film_slug))

        return items, next_url
                
    # Parse list url eg /jdemeza/watchlist/by/release/
    def _parse_list(self, list_url):
        i = 1
        
        logger.debug(f"Get page {i} of {list_url}")
        items, next_url = self._parse_items(f"{self.base_url}{list_url}")
        logger.debug(f"Processed page {i} of {list_url}") 
        
        while len(next_url) > 0:
            i += 1
            logger.debug(f"Get page {i} of {list_url}")
            next_items, next_url = self._parse_items(f"{self.base_url}{next_url}")
            items.extend(next_items)
            logger.debug(f"Processed page {i} of {list_url}")
        
        return items

    def _withRetry(self, url):
        retry_count = 3
        retry_sleep = 60
        retry_codes = [
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.GATEWAY_TIMEOUT,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.SERVICE_UNAVAILABLE,
            HTTPStatus.TOO_MANY_REQUESTS]

        for n in range(retry_count):
            try:
                if n > 0: # 0 based index
                    logger.debug(f"Sleep {retry_sleep}, attempt {n + 1}")

                    # Exponential backoff
                    if n > 1:
                        retry_sleep = retry_sleep * 2

                    time.sleep(retry_sleep)

                logger.debug(f"With retry {url}")

                response = requests.get(url)
                response.raise_for_status()
                
                return response
            except RequestException as e:
                logger.error(f"Request failed, exception: {e}")

                code = e.response.status_code
        
                if code in retry_codes:
                    continue

        logger.debug(f"Request failed, not retrying")

    # Get TMDB ids from a Letterboxd list
    def get_tmdb_ids(self, list_url):
        tmdb_ids = {}
        
        try:
            items = self._parse_list(list_url)
        
            for item in items:
                film_id, film_slug = item
            
                # Check cache first
                tmdb_id, letterboxd_id = self.cache.query_id_map_by_letterboxd(film_id)

                if tmdb_id is None:

                    response = self._withRetry(f"{self.base_url}/film/{film_slug}")
                    soup = BeautifulSoup(response.content, "html.parser")
                    body = soup.find('body')

                    str_tmdb_id = body.get("data-tmdb-id")

                    if not str_tmdb_id:
                        logger.debug(f"Could not find tmdb id for Letterboxd id {film_id}")
                        continue

                    tmdb_id = int(str_tmdb_id)
                    self.cache.add_id_map(tmdb_id, film_id, None)
                    logger.debug(f"Found tmdb id {tmdb_id} for Letterboxd id {film_id}, added to cache")
                else:
                    logger.debug(f"Found tmdb id {tmdb_id} for Letterboxd id {film_id} in cache")
            
                tmdb_ids[tmdb_id] = film_id
        except Exception as err:
            logger.error(f"Unable to parse Letterboxd list, exception: {err}")            
            tmdb_ids = None
            
        return tmdb_ids
    