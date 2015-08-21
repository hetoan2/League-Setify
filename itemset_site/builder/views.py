from django.shortcuts import render
from django.http import Http404, HttpRequest, HttpResponse
from .models import dd_version, get_build_from_match_id, ItemSet, Block, Summoner, get_summoner_id

import ast
import json
import urllib


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    itemset = ItemSet(include_consumables=True)
    context = {'itemset': itemset, 'version': dd_version, 'champion': '{championKey}'}
    return render(request, 'builder/results.html', context)


def game_builder(request, region, game_id, user_id):
    itemset = get_build_from_match_id(region, game_id, user_id)
    if itemset is None:
        return render(request, 'builder/error.html')
    context = {'itemset': itemset, 'version': dd_version, 'champion': itemset.champion}
    return render(request, 'builder/results.html', context)


def champ_builder(request, region, username, champion):
    summoner = get_summoner_id(username, region=region)

    # if summoner does not exist
    if not summoner:
        return render(request, 'games/error.html')
    # if there is a problem loading the matches, show this error
    if not summoner.get_matches(champion_name=champion):
        return render(request, 'games/error.html')

    # get item set from matches
    itemset = summoner.get_build_from_matches()
    itemset.title = username+"'s "+champion
    if itemset is None:
        return render(request, 'builder/error.html')
    context = {'itemset': itemset, 'version': dd_version, 'champion': champion}
    if summoner.get_matches(champion_name=champion):
        return render(request, 'builder/results.html', context)
    else:
        return render(request, 'builder/error.html')


def json_generate(request):
    if request.method == "POST":
        post = request.POST
        # convert the itemset data into an array (safely)
        data = ast.literal_eval(post['itemset-data'])
        itemset = ItemSet(include_consumables=False)

        # set the name of the item set
        itemset.title = post['setname']

        # set the map for the itemset
        if post['map'] == "All Maps":
            itemset.map = "any"
        elif post['map'] == "Summoner's Rift":
            itemset.map = "SR"
        elif post['map'] == "Howling Abyss":
            itemset.map = "HA"
        elif post['map'] == "Twisted Treeline":
            itemset.map = "TT"
        elif post['map'] == "Crystal Scar":
            itemset.map = "CS"

        # set the mode for the itemset
        if post['mode'] == "All Modes":
            itemset.mode = "any"
        elif post['mode'] == "Classic (5v5/3v3)":
            itemset.mode = "CLASSIC"
        elif post['mode'] == "ARAM":
            itemset.mode = "ARAM"
        elif post['mode'] == "Dominion":
            itemset.mode = "ODIN"

        for block_data in data:
            # empty blocks are excluded, they should only contain their name and will have length of 1
            if len(block_data) > 1:
                block = Block()
                block.type = block_data[0]      # first index in array is the name of the block
                for item_id in block_data[1:]:  # rest of the items in block data list will be item ids
                    block.add_item_from_form(item_id)
                # add block to item set
                itemset.add_block(block)
        return HttpResponse(json.dumps(itemset.generate()), content_type="application/json")
    else:
        return render(request, 'builder/error.html')