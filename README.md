# Movie Sync

1. Get all TMDB ids from a Letterboxd list, build up a cache (sql lite).
1. Get all TMDB ids from a Plex collection, build up a cache (sql lite).
1. For each TMDB id that is in the Plex collection but not in the Letterboxd list, remove the Plex collection item.
1. For each TMDB id that is in the Letterboxd list but not in the Plex collection, add the Plex collection item.
	1.  If the TMDB id is also not in the Plex collection, add the item to Radarr.
1. Reorder the Plex collection to align with the Letterboxd list.