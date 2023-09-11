import logging

logger = logging.getLogger(__name__)

class LetterboxdExport:    
    def __init__(self, letterboxd, plex, radarr):
        self.letterboxd = letterboxd
        self.plex = plex
        self.radarr = radarr
        
    # Add items to Plex
    def _add_to_plex(self, letterboxd_ids, plex_collection_id, plex_ids):
        not_plex = set(letterboxd_ids.keys()).difference(plex_ids.keys())
        # added = {}        # tmdb_id, plex_id, fromcache
        # not_found = []    # tmdb_id
        added, not_found = self.plex.add_items(plex_collection_id, not_plex)
        if added:
            plex_ids.update(added)
        
        return not_found

    # Add items to Radarr
    def _add_to_radarr(self, letterboxd_ids, not_found):
        if not_found:
            for radarr_tmdb in not_found:
                radarr_movie = self.radarr.get_movie(radarr_tmdb)
    
                if radarr_movie is not None and not radarr_movie:
                    logger.debug(f"Can't find movie {radarr_tmdb} in Radarr")
            
                    if self.radarr.add_movie(radarr_tmdb):
                        logger.debug(f"Added movie {radarr_tmdb} to Radarr")
        
                # Not in Plex after add, so need to be excluded from Letterboxd sort
                del(letterboxd_ids[radarr_tmdb])
            
    # Get Plex collection based on title
    def _get_plex_collection_id(self, plex_collection_title):
        logger.debug(f"Get Plex collection based on title: {plex_collection_title}")
        
        plex_collections = self.plex.get_collection_ids(plex_collection_title)
    
        if plex_collections:
            return plex_collections[0]
    
        return 0
            
    # Remove items from Plex
    def _remove_from_plex(self, letterboxd_ids, collection_id, plex_ids):
        not_letterboxd = set(plex_ids.keys()).difference(letterboxd_ids.keys())
        for key in not_letterboxd:
            if self.plex.remove_item(collection_id, plex_ids[key]):
                del(plex_ids[key])
            
    # Sort Plex items
    def _sort_plex_list(self, letterboxd_ids, collection_id, plex_ids):
        plex_id_keys = list(plex_ids.keys())
        previous = None

        for i, item in enumerate(letterboxd_ids, 0):
            if item != plex_id_keys[i]:
                # Out of order, determine current place in the list
                idx = plex_id_keys.index(item)
                actual = plex_ids[plex_id_keys[idx]]
            
                if self.plex.move_item(collection_id, actual, previous):        
                    logger.debug(f"Moved {actual} after {previous}")
        
                    plex_id_keys.insert(i, plex_id_keys.pop(idx))
        
            # Update current position
            previous = plex_ids[plex_id_keys[i]] 

    # Sync with Plex and Radarr
    def to_plex(self, letterboxd_list, plex_collection_title):
        logger.info(f"Starting sync between Letterboxd list ({letterboxd_list}) and Plex collection ({plex_collection_title}).")    
                 
        plex_collection_id = self._get_plex_collection_id(plex_collection_title)
    
        if plex_collection_id == 0:
            raise Exception("Unable to retrieve Plex collection.")

        # Get TMDB ids from the Letterboxd list
        logger.debug(f"Parsing Letterboxd list: {letterboxd_list}")
        letterboxd_ids = self.letterboxd.get_tmdb_ids(letterboxd_list)
        if letterboxd_ids is None:
            raise Exception("Unable to retrieve Letterboxd list items.")

        # Get TMDB ids from the Plex collection
        logger.debug(f"Parsing Plex collection: {plex_collection_title}")
        plex_ids = self.plex.get_tmdb_ids(plex_collection_id)
        if plex_ids is None:
            raise Exception("Unable to retrieve Plex collection items.")
        
        # Items that are in Plex but not Letterboxd, remove from Plex.
        logger.debug("Removing items from Plex collection that aren't in Letterboxd.")
        self._remove_from_plex(letterboxd_ids, plex_collection_id, plex_ids)

        # Items that are in Letterboxd but not Plex, add to Plex.
        logger.debug("Adding items from Letterboxd that aren't in Plex collection.")
        not_found = self._add_to_plex(letterboxd_ids, plex_collection_id, plex_ids)
    
        # If the item is also not in the Plex collection, add the item to Radarr.
        logger.debug("Adding items to Radarr that aren't in Plex collection.")
        self._add_to_radarr(letterboxd_ids, not_found)

        # Letterboxd list and Plex collection should now be the same length for sorting
        logger.debug("Sorting Plex collection.")
        self._sort_plex_list(letterboxd_ids, plex_collection_id, plex_ids)

        logger.info(f"Finished sync between Letterboxd list ({letterboxd_list}) and Plex collection ({plex_collection_id}).")
        