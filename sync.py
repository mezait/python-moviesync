import asyncio
import logging
import sys

from moviesync.cache import Cache
from moviesync.config import Config
from moviesync.letterboxd import Letterboxd
from moviesync.letterboxdexport import LetterboxdExport
from moviesync.plex import Plex
from moviesync.radarr import Radarr

logging.basicConfig(level=logging.INFO)
logging.getLogger("moviesync").setLevel(logging.DEBUG)
# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.getLogger("uc").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)
# logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("zendriver").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# sync.py "<path_to_letterboxd_list>" "<name_of_plex_collection>"
if __name__ == "__main__":
    if len(sys.argv) != 3:
        logger.error("Invalid number of params")
        sys.exit(1)  # error

    cache = Cache()
    config = Config.load()
    letterboxd = Letterboxd(cache)
    plex = Plex(config, cache)
    radarr = Radarr(config)

    letterboxdexport = LetterboxdExport(letterboxd, plex, radarr)

    try:
        asyncio.run(letterboxdexport.to_plex(sys.argv[1], sys.argv[2]))
    except Exception as err:
        logger.error(f"Failed to export from Letterboxd to Plex, exception: {err}")
        sys.exit(1)  # error
