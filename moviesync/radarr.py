import logging
import requests
from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)

class Radarr:
    def __init__(self, config):
        self.base_url = config['radarr']['url']
        self.api_key = config['radarr']['apikey']
        self.quality_profile = config['radarr']['quality_profile']
        self.root_folder_path = config['radarr']['root_folder_path']

    # Get movie from Radarr based on TMDB id
    def get_movie(self, tmdb_id):
        try:
            response = requests.get(f"{self.base_url}/api/v3/movie?apikey={self.api_key}&tmdbId={tmdb_id}")
            response.raise_for_status()
            
            # If not found, empty array
            return response.json()
        except HTTPError as err:
            logger.error(f"Could not get movie from Radarr: {err}")
            
        return None
    
    # Add movie to Radarr based on TMDB id
    def add_movie(self, tmdb_id):
        data = {
            "tmdbId": tmdb_id,
            "monitored": True,
            "qualityProfileId": self.quality_profile,
            "minimumAvailability": "announced",
            "addOptions": {
                "searchForMovie": True
            },
            "rootFolderPath": self.root_folder_path,
            "title": f"tmdb-{tmdb_id}"
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/v3/movie?apikey={self.api_key}", json=data)
            response.raise_for_status()
            
            return response.json()
        except HTTPError as err:
            logger.error(f"Could not add movie to Radarr: {err}")
            
        return None