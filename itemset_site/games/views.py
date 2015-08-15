from django.shortcuts import render
from django.http import HttpResponse, Http404
from .models import Summoner, get_summoner_id


# Create your views here.
def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    # context = {'latest_question_list': latest_question_list}
    return render(request, 'games/index.html')


def results(request, username):
    summoner = get_summoner_id(username)
    summoner.get_matches()
    return render(request, 'games/results.html', {'summoner': summoner})
    # return HttpResponse("You're looking at question %s." % question_id)


def champ_results(request, username, champion):
    summoner = get_summoner_id(username)
    summoner.get_matches(champion_name=champion)
    return render(request, 'games/results.html', {'summoner': summoner})

# def results(request, question_id):
#     response = "You're looking at the results of question %s."
#     return HttpResponse(response % question_id)
#
#
# def vote(request, question_id):
#     return HttpResponse("You're voting on question %s." % question_id)