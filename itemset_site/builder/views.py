from django.shortcuts import render
from .models import dd_version, get_build_from_match_id
import json
import urllib

# Create your views here.
def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    context = {'version': dd_version}
    return render(request, 'builder/index.html', context)


def game_builder(request, region, game_id, user_id):
    itemset = get_build_from_match_id(region, game_id, user_id)
    context = {'itemset': itemset, 'version': dd_version}
    return render(request, 'builder/results.html', context)