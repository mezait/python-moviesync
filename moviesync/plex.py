import logging

from plexapi.exceptions import NotFound
from plexapi.server import PlexServer

logger = logging.getLogger(__name__)


class Plex:
    def __init__(self, config, cache):
        plex = PlexServer(config["plex"]["url"], config["plex"]["token"])

        self.plex_library = plex.library.section(config["plex"]["movie_library_name"])
        self.cache = cache

    # Add items to Plex collection based on TMDB id
    def add_items(self, collection_title, tmdb_ids):
        in_plex = {}  # tmdb_id, plex_id
        not_in_plex = []  # tmdb_id

        for tmdb_id in tmdb_ids:
            # Check cache first
            tmdb_id, letterboxd_id, plex_id = self.cache.query_id_map(tmdb_id)

            if plex_id is None:
                # Not in cache, search Plex by TMDB id
                plex_item = None

                try:
                    plex_item = self.plex_library.getGuid(f"tmdb://{tmdb_id}")
                except NotFound:
                    pass

                if plex_item is not None:
                    self.cache.add_id_map(tmdb_id, None, plex_item.ratingKey)
                    logger.debug(
                        f"Found TMDB id {tmdb_id} for Plex id {plex_item.ratingKey}, added to cache"
                    )
                    in_plex[tmdb_id] = plex_item.ratingKey
                else:
                    logger.debug(f"TMDB id {tmdb_id} not in Plex")
                    not_in_plex.append(tmdb_id)
            else:
                logger.debug(f"Found TMDB id {tmdb_id} for Plex id {plex_id} in cache")
                in_plex[tmdb_id] = plex_id

        # Nothing in Plex that isn't already in the collection, nothing to do
        if not in_plex:
            return None, not_in_plex

        for tmdb_id in in_plex:
            try:
                plex_item = self.plex_library.fetchItem(in_plex[tmdb_id])
                plex_item.addCollection(collection_title)
            except Exception as err:
                logger.error(f"Unable to add Plex item, exception: {err}")

        return in_plex, not_in_plex

    # Get TMDB ids from a Plex collection
    def get_tmdb_ids(self, collection_title):
        tmdb_ids = {}

        try:
            collection = self.plex_library.collection(collection_title)

            for item in collection.items():
                # Check cache first
                tmdb_id, plex_id = self.cache.query_id_map_by_plex(item.ratingKey)

                if tmdb_id is None:
                    for guid in item.guids:
                        if guid.id.startswith("tmdb://"):
                            tmdb_id = int(guid.get("id").replace("tmdb://", ""))
                            self.cache.add_id_map(tmdb_id, None, item.ratingKey)
                            logger.debug(
                                f"Found TMDB id {tmdb_id} for Plex id {item.ratingKey}, added to cache"
                            )
                            break
                else:
                    logger.debug(
                        f"Found TMDB id {tmdb_id} for Plex id {item.ratingKey} in cache"
                    )

                tmdb_ids[tmdb_id] = item.ratingKey
        except Exception as err:
            logger.error(f"Unable to parse Plex collection, generic exception: {err}")
            tmdb_ids = None

        return tmdb_ids

    # Move an item within a collection
    def move_item(self, collection_title, item_id, after_id):
        try:
            collection = self.plex_library.collection(collection_title)

            item_to_move = collection.fetchItem(item_id)
            item_before = None

            if after_id is not None:
                item_before = collection.fetchItem(after_id)

            collection.moveItem(item_to_move, item_before)

            return True
        except Exception as err:
            logger.error(f"Unable to move Plex item, exception: {err}")

        return False

    # Remove an item from a Plex collection
    def remove_item(self, collection_title, item_id):
        try:
            collection = self.plex_library.collection(collection_title)

            item_to_remove = collection.fetchItem(item_id)

            collection.removeItems(item_to_remove)

            return True
        except Exception as err:
            logger.error(f"Unable to remove Plex item, exception: {err}")

        return False
