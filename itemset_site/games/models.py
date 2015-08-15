from django.db import models
import urllib
import json

# Create your models here.
# api_key = open("api_key.txt", "r").read().replace('\n', '')
# print "Using api key: " + api_key

api_key = ""

dd_version = json.load(urllib.urlopen("https://global.api.pvp.net/api/lol/static-data/na/v1.2/versions"
                                      "?api_key=" + api_key))[0]

# print "Using DataDragon version: " + dd_version

champion_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com"
                                         "/cdn/" + dd_version + "/data/en_US/champion.json"))

item_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com/cdn/" + dd_version + "/data/en_US/item.json"))

summoner_spell_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com"
                                               "/cdn/" + dd_version + "/data/en_US/summoner.json"))


class Summoner(object):
    def __init__(self, summoner_object, region="na"):
        self.id = summoner_object['id']
        self.name = summoner_object['name']
        self.matches = list()
        self.participant_ids = list()
        self.participant_id = 0
        self.version = dd_version
        self.region = region

    def get_matches(self, champion_name=None, ranked=None):
        """
        Get a list of match IDs for this summoner
        :param champion_name: String containing the champion name to filter games for
        :param ranked: Boolean on whether to restrict to soloq games or not.
        :return:
        """
        query_params = {}
        url = "https://na.api.pvp.net/api/lol/" + self.region + "/v2.2/matchhistory/" + str(self.id) + "?"

        if ranked == 1:
            query_params['rankedQueues'] = 'RANKED_SOLO_5x5'
        elif ranked == 2:
            query_params['rankedQueues'] = 'RANKED_TEAM_3x3'
        elif ranked == 3:
            query_params['rankedQueues'] = 'RANKED_TEAM_5x5'

        # query_params['beginIndex'] = 10
        # query_params['endIndex'] = 100

        if champion_name is not None:
            champion_id = get_champion_id(champion_name)
            query_params['championIds'] = champion_id

        query_params['api_key'] = api_key

        # add the query parameters to the url
        url += urllib.urlencode(query_params)

        # get the response from the server
        response = urllib.urlopen(url)
        data = json.load(response)

        try:
            self.matches = list()
            for match in data['matches']:
                stats = match['participants'][0]['stats']
                match_data = {"id": match['matchId'],
                              "champ": get_champion_name(match['participants'][0]['championId']),
                              "score": "%s/%s/%s" % (stats['kills'], stats['deaths'], stats['assists']),
                              "spell_1": get_summoner_spell_image(match['participants'][0]['spell1Id']),
                              "spell_2": get_summoner_spell_image(match['participants'][0]['spell2Id']),
                              # for version, replace find second decimal place (replace first decimal with space,
                              # then do find on result to get index of second decimal, strip to base version
                              # finally adding ".1" to end of version number to get the data dragon variant.
                              "version": match['matchVersion']
                                         [:match['matchVersion'].replace(".", " ", 1).find(".")] + ".1",
                              "status": stats['winner']
                              }
                item_slots = ['0', '1', '2', '3', '4', '5', '6']
                for slot in item_slots:
                    if stats['item' + slot] != 0:
                        match_data[slot] = stats['item' + slot]
                self.matches.append(match_data)
        except KeyError:
            # if there are no matches, create a blank list.
            self.matches = []

        self.participant_ids = []

    def get_timeline_data(self, match_index):
        """
        Obtain the timeline data from the API for the match index in the list.
        :param match_index: Int containing index of the match to lookup in the match list.
        :return: Json Array of frames from the timeline, Int Participant ID of the summoner in the match.
        """
        # if no matches exist, then do not attempt a match lookup
        if len(self.matches) != 0:
            try:
                match = self.matches[match_index]
            except IndexError:
                # if we are out of index, just return the latest game.
                match = self.matches[-1]
            url = "https://na.api.pvp.net/api/lol/" + self.region + "/v2.2/match/" + str(match["id"]) + \
                  "?includeTimeline=true&api_key=" + api_key

            response = urllib.urlopen(url)
            data = json.load(response)
            participant_id = -1
            for participant in data['participantIdentities']:
                if participant['player']['summonerId'] == self.id:
                    participant_id = participant['participantId']
            return data['timeline']['frames'], participant_id

            # def get_build_from_match_index(self, match_index):
            # """
            #     Get the item set for the match specified by it's index in the list.
            #     :param match_index: Int index of the match in the match list.
            #     :return: String with Item Set Json
            #     """
            #     timeline_data, participant_id = self.get_timeline_data(match_index)
            #     # generate a new item set from the events in the match
            #     item_set = ItemSet()
            #     for frame in timeline_data:
            #         try:
            #             events = frame['events']
            #             for event in events:
            #                 if event['eventType'] == 'ITEM_PURCHASED' and event['participantId'] == participant_id:
            #                     # print event
            #                     item_set.add_item(correct_item_id(event['itemId']), event['timestamp'])
            #                 if event['eventType'] == 'ITEM_UNDO' and event['participantId'] == participant_id:
            #                     # print event
            #                     # if the user undid a sell, then we should not undo the purchase
            #                     if event['itemBefore'] != 0:
            #                         item_set.undo_purchase()
            #             item_set.add_auto_block()
            #         except KeyError:
            #             pass
            #     return json.dumps(item_set.generate())


def get_champion_id(champion_name):
    """
    Get the champion ID from a champion's name.
    :param champion_name: String with champion's name.
    :return: String with champion id
    """
    return champion_data['data'][champion_name]['key']


def get_champion_name(champion_id):
    for champ in champion_data['data']:
        if champion_data['data'][champ]['key'] == str(champion_id):
            return champ


def get_summoner_id(username, region="na"):
    """
    Get the summoner from the API using the username.
    :param username: String with username to lookup.
    :param region: String with region to lookup in.
    :return: Summoner object for the user.
    """
    url = "https://na.api.pvp.net/api/lol/" + region + "/v1.4/summoner/by-name/" + username + "?api_key=" + api_key
    response = urllib.urlopen(url.encode("UTF-8"))
    data = json.load(response)
    return Summoner(data[data.keys()[0]], region=region)


def get_summoner_spell_image(spell_id):
    # print spell_id
    for spell in summoner_spell_data['data']:
        if summoner_spell_data['data'][spell]['key'] == str(spell_id):
            return spell
            # return summoner_spell_data['data'][spell]['image']['full']
    return "SummonerFlash"