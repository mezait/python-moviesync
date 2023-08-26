import logging
import lxml.etree
import requests
from moviesync import utils

logger = logging.getLogger(__name__)

class Plex:
    def __init__(self, config, cache):
        self.base_url = config['plex']['url']
        self.x_plex_token = config['plex']['token']       
        self.library_id = config['plex']['movie_library_id']  
        self.cache = cache
        
    # Get all rating keys based on filter
    def _get_all_rating_keys(self, filters):
        rating_keys = []
        
        response = requests.get(f"{self.base_url}/library/sections/{self.library_id}/all?X-Plex-Token={self.x_plex_token}{utils.parse_html_params(filters)}")
        response.raise_for_status()

        root = lxml.etree.fromstring(response.content)

        for video in root.findall("Video"):
            rating_keys.append(int(video.get("ratingKey")))
            
        return rating_keys
        
    # Get the machine identifier from the token
    def _get_machine_identitier(self):
        response = requests.get(f"{self.base_url}/identity?X-Plex-Token={self.x_plex_token}")
        response.raise_for_status()                

        root = lxml.etree.fromstring(response.content)

        return root.get("machineIdentifier")
    
    # Get the Plex server path from the machine identifier
    def _get_server_path(self):
        return f"server://{self._get_machine_identitier()}/com.plexapp.plugins.library"
    
    # Use the match hack to find a plex movie based on TMDB id
    def _get_by_tmdbid(self, rating_key, tmdb_id):
        # https://forums.plex.tv/t/discover-future-movies/816009/7
        response = requests.get(f"{self.base_url}/library/metadata/{rating_key}/matches?X-Plex-Token={self.x_plex_token}&manual=1&title=tmdb-{tmdb_id}")
        response.raise_for_status()
        
        root = lxml.etree.fromstring(response.content)

        return root.find("SearchResult").get("guid")
    
    # Add items to Plex collection based on tmdb id
    def add_items(self, collection_id, tmdb_ids):
        try:
            dummy_rating_key = self._get_all_rating_keys({ "limit" : 1 })[0]
        except Exception as err:
            logger.error(f"Unable to retrieve dummy rating key, exception: {err}")
            
            return None, None
        
        in_plex = {} # tmdb_id, plex_id
        not_in_plex = [] # tmdb_id
        
        for tmdb_id in tmdb_ids:
            try:    
                # Check cache first
                tmdb_id, letterboxd_id, plex_id = self.cache.query_id_map(tmdb_id)
            
                if plex_id is None:
                    # Not in cache, search Plex by TMDB id
                    plex_guid = self._get_by_tmdbid(dummy_rating_key, tmdb_id)
                    rating_keys = self._get_all_rating_keys({ "guid": plex_guid })
                
                    if rating_keys:
                        plex_id = rating_keys[0]
                        self.cache.add_id_map(tmdb_id, None, plex_id)
                        logger.debug(f"Found TMDB id {tmdb_id} for Plex id {plex_id}, added to cache")                 
                        in_plex[tmdb_id] = plex_id
                    else:
                        logger.debug(f"{tmdb_id} not in Plex")
                        not_in_plex.append(tmdb_id)
                else:                
                    logger.debug(f"Found TMDB id {tmdb_id} for Plex id {plex_id} in cache")
                    in_plex[tmdb_id] = plex_id
            except Exception as err:
                logger.error(f"Unable to find Plex item, exception: {err}")
        
        if in_plex:
            try:
                geturi = f"{self._get_server_path()}/library/metadata/{','.join(map(lambda x: str(x), in_plex.values()))}"
                puturi = f"{self.base_url}/library/collections/{collection_id}/items?X-Plex-Token={self.x_plex_token}&uri={geturi}"
                
                response = requests.put(puturi)
                response.raise_for_status()        
            except Exception as err:
                logger.error(f"Unable to add Plex items, exception: {err}")
                in_plex = None

        return in_plex, not_in_plex
    
    # Get collections, can filter by title.
    def get_collection_ids(self, title):
        rating_keys = []
        
        uri = f"{self.base_url}/library/sections/{self.library_id}/collections?X-Plex-Token={self.x_plex_token}"
        
        if title is not None:
            params = utils.parse_html_params({ "title": title })
            uri = f"{uri}{params}"
            
        try:
            response = requests.get(uri)
            response.raise_for_status()
            
            root = lxml.etree.fromstring(response.content)
            
            for directory in root.findall("Directory"):
                rating_keys.append(int(directory.get("ratingKey")))

            return rating_keys
        except Exception as err:
            logger.error(f"Unable to get Plex collection id(s), exception: {err}")

        return None

    # Get TMDB ids from a Plex collection
    def get_tmdb_ids(self, collection_id):
        tmdb_ids = {}
        
        try:
            response = requests.get(f"{self.base_url}/library/metadata/{collection_id}/children?X-Plex-Token={self.x_plex_token}&includeGuids=1")
            response.raise_for_status()                
        
            root = lxml.etree.fromstring(response.content)
        
            for video in root.findall("Video"):
                rating_key = int(video.get("ratingKey"))
            
                # Check cache first
                tmdb_id, plex_id = self.cache.query_id_map_by_plex(rating_key)
            
                if tmdb_id is None:
                    guid = video.xpath("Guid[starts-with(@id, 'tmdb://')]")[0]
                    tmdb_id = int(guid.get("id").replace("tmdb://",""))
                    self.cache.add_id_map(tmdb_id, None, rating_key)
                    logger.debug(f"Found TMDB id {tmdb_id} for Plex id {rating_key}, added to cache")
                else:
                    logger.debug(f"Found TMDB id {tmdb_id} for Plex id {rating_key} in cache")
        
                tmdb_ids[tmdb_id] = rating_key
        except Exception as err:
            logger.error(f"Unable to parse Plex collection, generic exception: {err}")            
            tmdb_ids = None

        return tmdb_ids
        
    # Move an item within a collection
    def move_item(self, collection_id, item_id, after_id):
        uri = f"{self.base_url}/library/collections/{collection_id}/items/{item_id}/move?X-Plex-Token={self.x_plex_token}"        
        
        if after_id is not None:
            params = utils.parse_html_params({ "after": after_id })            
            uri = f"{uri}{params}"
        
        try:
            response = requests.put(uri)
            response.raise_for_status()
            
            return True        
        except Exception as err:
            logger.error(f"Unable to move Plex item, exception: {err}")
            
        return False
        
    # Remove an item from a Plex collection
    def remove_item(self, collection_id, item_id):
        try:
            response = requests.delete(f"{self.base_url}/library/collections/{collection_id}/items/{item_id}?X-Plex-Token={self.x_plex_token}")
            response.raise_for_status()
            
            return True
        except Exception as err:
            logger.error(f"Unable to remove Plex item, exception: {err}")
            
        return False
