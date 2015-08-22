from django.db import models
from django.core.cache import cache
import json
import urllib

api_key = ""

dd_version = cache.get('version')

# if the version number is not in the cache (expired), fetch data again
if dd_version is None:
    valid_lookup = False
    while not valid_lookup:
        try:
            versions = json.load(urllib.urlopen("https://global.api.pvp.net/api/lol/static-data/na/v1.2/versions"
                                                "?api_key=" + api_key))

            dd_version = versions[0]

            # cache the versions every 8 hours.
            cache.set(dd_version, 'version', 60*60*8)

            valid_lookup = True
        except:
            valid_lookup = False