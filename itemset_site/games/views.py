from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import get_summoner_id


# cache the results 15 minutes (games take longer than this)
@cache_page(60 * 15)
def results(request, region, username):
    try:
        summoner = get_summoner_id(username, region=region)
        summoner.get_matches()

        return render(request, 'games/results.html', {'summoner': summoner, 'singlechamp': False})
    except LookupError:
        return render(request, 'games/error.html')


# cache the results 15 minutes (games take longer than this)
@cache_page(60 * 15)
def champ_results(request, region, username, champion):
    try:
        summoner = get_summoner_id(username, region=region)
        if summoner.get_matches(champion_name=champion):
            return render(request, 'games/results.html', {'summoner': summoner, 'singlechamp': True})
    except LookupError:
        return render(request, 'games/error.html')