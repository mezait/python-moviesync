import logging
import sqlite3
from contextlib import closing

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self):
        self.path = "moviesync.cache"
        
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            with closing(connection.cursor()) as cursor:
                cursor.execute("SELECT COUNT(name) FROM sqlite_master WHERE type='table' AND name='id_map'")                
                if cursor.fetchone()[0] == 0:
                    logger.debug(f"Initializing cache database at {self.path}")
                else:
                    logger.debug(f"Using cache database at {self.path}")
                  
                # cursor.execute("DROP TABLE IF EXISTS id_map")
              
                cursor.execute(
                    """CREATE TABLE IF NOT EXISTS id_map (
                    tmdb_id         INTEGER PRIMARY KEY,
                    letterboxd_id   INTEGER,
                    plex_id         INTEGER)"""
                )
      
    # Add item to cache
    def add_id_map(self, tmdb_id, letterboxd_id, plex_id):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            with closing(connection.cursor()) as cursor:                
                cursor.execute(f"INSERT OR IGNORE INTO id_map(tmdb_id) VALUES(?)", (tmdb_id,))
                if letterboxd_id is not None:
                    cursor.execute(f"UPDATE id_map SET letterboxd_id = ? WHERE tmdb_id = ?", (letterboxd_id, tmdb_id))
                if plex_id is not None:                    
                    cursor.execute(f"UPDATE id_map SET plex_id = ? WHERE tmdb_id = ?", (plex_id, tmdb_id))
                    
    # Find cached item by TMDB id
    def query_id_map(self, tmdb_id):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            with closing(connection.cursor()) as cursor:
                cursor.execute(f"SELECT tmdb_id, letterboxd_id, plex_id FROM id_map WHERE tmdb_id = ?", (tmdb_id,))
                row = cursor.fetchone()
                if row:
                    return row["tmdb_id"], row["letterboxd_id"], row["plex_id"]
        
        return None, None, None
    
    # Find cached item by Letterboxd id
    def query_id_map_by_letterboxd(self, letterboxd_id):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row            
            with closing(connection.cursor()) as cursor:
                cursor.execute(f"SELECT tmdb_id, letterboxd_id FROM id_map WHERE letterboxd_id = ?", (letterboxd_id,))
                row = cursor.fetchone()
                if row:
                    return row["tmdb_id"], row["letterboxd_id"]
                
        return None, None
    
    # Find cached item by Plex id
    def query_id_map_by_plex(self, plex_id):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row            
            with closing(connection.cursor()) as cursor:
                cursor.execute(f"SELECT tmdb_id, plex_id FROM id_map WHERE plex_id = ?", (plex_id,))
                row = cursor.fetchone()
                if row:
                    return row["tmdb_id"], row["plex_id"]
                
        return None, None
                        
    # Unset Plex id in cache
    def unset_plex_id(self, tmdb_id):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            with closing(connection.cursor()) as cursor:
                cursor.execute(f"UPDATE id_map SET plex_id = NULL WHERE tmdb_id = ?", (tmdb_id,))