from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Summoner, get_summoner_id


def results(request, region, username):
    summoner = get_summoner_id(username, region=region)
    # if summoner object is false, then there was an error looking up the player's name
    if not summoner:
        return render(request, 'games/error.html')
    # if get_matches returns false, then there was an error
    if summoner.get_matches():
        return render(request, 'games/results.html', {'summoner': summoner, 'singlechamp': False})
    else:
        return render(request, 'games/error.html')
    # return HttpResponse("You're looking at question %s." % question_id)


def champ_results(request, region, username, champion):
    summoner = get_summoner_id(username, region=region)
    if not summoner:
        return render(request, 'games/error.html')
    if summoner.get_matches(champion_name=champion):
        return render(request, 'games/results.html', {'summoner': summoner, 'singlechamp': True})
    else:
        return render(request, 'games/error.html')

# def results(request, question_id):
#     response = "You're looking at the results of question %s."
#     return HttpResponse(response % question_id)
#
#
# def vote(request, question_id):
#     return HttpResponse("You're voting on question %s." % question_id)