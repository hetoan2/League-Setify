__author__ = 'hetoan2'

import urllib
import json
import datetime


api_key = open("api_key.txt", "r").read().replace('\n', '')
print "Using api key: " + api_key

dd_version = json.load(urllib.urlopen("https://global.api.pvp.net/api/lol/static-data/na/v1.2/versions"
                                      "?api_key=" + api_key))[0]

print "Using DataDragon version: " + dd_version

champion_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com"
                                         "/cdn/" + dd_version + "/data/en_US/champion.json"))

item_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com/cdn/" + dd_version + "/data/en_US/item.json"))


class ItemSet(object):
    def __init__(self, include_consumables=True):
        """
        Initialize the item set.
        :param include_consumables: Boolean, if True, will generate the first block with consumables for quick purchases
        :return:
        """
        self.title = "Generated Item Set"
        self.type = "custom"
        self.map = "any"
        self.mode = "any"
        self.priority = False
        self.sortrank = 5
        self.blocks = list()
        self.auto_block = Block()
        self.last_timestamp = 0

        if include_consumables:
            consumable_block = Block()
            consumable_block.type = "Consumables"
            for item in item_data['data']:
                # could exclude non-purchasable items, but they don't show up in shop anyway
                if 'Consumable' in item_data['data'][item]['tags']:
                    consumable_block.add_item(item)
            # sort the consumable block
            consumable_block.sort()
            self.blocks.append(consumable_block)

    def add_block(self, block):
        """
        Add a block to the list of blocks
        :param block: The block of items to add
        :return:
        """
        self.blocks.append(block)

    def add_item(self, item_id, timestamp):
        """
        Add the item id to the automatically generated block, adding a new block if necessary.
        :param item_id: Item ID to add
        :param timestamp: Time of item purchase.
        :return:
        """
        # automatically add our block if it has been a minute since last purchase
        if timestamp - self.last_timestamp > 60000 and not self.auto_block.is_empty():
            self.add_auto_block()

        self.auto_block.add_item(item_id)
        self.last_timestamp = timestamp

    def undo_purchase(self):
        """
        Reset the automatically generated block if purchase was undone.
        :return:
        """
        self.auto_block = Block()

    def add_auto_block(self):
        """
        Automatically Generated blocks based off timestamp information will use this method to add blocks to the list
        :return:
        """
        time = datetime.timedelta(milliseconds=self.last_timestamp)
        minutes, seconds = divmod(time.seconds, 60)
        self.auto_block.type = "%02d:%02d        |           |   |" % (minutes, seconds)
        self.blocks.append(self.auto_block)
        self.auto_block = Block()

    def generate(self):
        """
        Generate the json object for this class
        :return:
        """
        json_object = dict()
        json_object["title"] = self.title
        json_object["type"] = self.type
        json_object["map"] = self.map
        json_object["mode"] = self.mode
        json_object["priority"] = self.priority
        json_object["sortrank"] = self.sortrank
        json_object["blocks"] = [block.generate() for block in self.blocks]
        return json_object


class Block(object):
    def __init__(self):
        self.type = "Block Title"
        self.recMath = False
        self.minSummonerLevel = -1
        self.maxSummonerLevel = -1
        self.showIfSummonerSpell = ""
        self.hideIfSummonerSpell = ""
        self.items = list()

    def add_item(self, item_id):
        """
        Add an item to the block, automatically grouping quantities of identical items
        :param item_id: The item id to add to the block
        :return:
        """
        for item in self.items:
            if item["id"] == str(item_id):
                item["count"] += 1
                return
        self.items.append({"id": str(item_id), "count": 1})

    def remove_item(self, item_id):
        """
        Remove a single item from the block, if multiples exist, will decrement the number in the block.
        :param item_id: Item id to remove (one of) from the block.
        :return:
        """
        for item in self.items:
            if item["id"] == str(item_id):
                if item["count"] == 1:
                    self.items.remove(item)
                else:
                    item["count"] -= 1

    def is_empty(self):
        """
        Atomic statement for if the block is currently empty.
        :return: True if block is empty.
        """
        return len(self.items) == 0

    def sort(self):
        """
        Sorts the items in the block by their price ascending.
        :return:
        """
        self.items = sorted(self.items, key=lambda item: item_data['data'][item["id"]]['gold']['total'])

    def generate(self):
        """
        Generate the json object for this class
        :return: Dictionary with correct json object structure for the item set Block
        """
        json_object = dict()
        json_object["type"] = self.type
        json_object["recMath"] = self.recMath
        json_object["minSummonerLevel"] = self.minSummonerLevel
        json_object["maxSummonerLevel"] = self.maxSummonerLevel
        json_object["showIfSummonerSpell"] = self.showIfSummonerSpell
        json_object["hideIfSummonerSpell"] = self.hideIfSummonerSpell
        json_object["items"] = self.items
        return json_object


class Summoner(object):
    def __init__(self, summoner_object):
        self.id = summoner_object['id']
        self.name = summoner_object['name']
        self.matches = list()
        self.participant_ids = list()
        self.participant_id = 0

    def get_matches(self, champion_name=None, ranked=None):
        """
        Get a list of match IDs for this summoner
        :param champion_name: String containing the champion name to filter games for
        :param ranked: Boolean on whether to restrict to soloq games or not.
        :return:
        """
        query_params = {}
        url = "https://na.api.pvp.net/api/lol/na/v2.2/matchhistory/" + str(self.id) + "?"

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
                              "champ": match['participants'][0]['championId'],
                              "score": "%s/%s/%s" % (stats['kills'], stats['deaths'], stats['assists']),
                              "spell_1": match['participants'][0]['spell1Id'],
                              "spell_2": match['participants'][0]['spell2Id'],
                              # for version, replace find second decimal place (replace first decimal with space,
                              # then do find on result to get index of second decimal, strip to base version
                              # finally adding ".1" to end of version number to get the data dragon variant.
                              "version": match['matchVersion']
                                         [:match['matchVersion'].replace(".", " ", 1).find(".")] + ".1"
                }
                item_slots = ['0', '1', '2', '3', '4', '5', '6']
                for slot in item_slots:
                    if stats['item'+slot] != "0":
                        match_data[slot] = stats['item'+slot]
                self.matches.append(match_data)
        except KeyError:
            # if there are no matches, create a blank list.
            self.matches = []

        self.participant_ids = []
        print self.matches

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
            url = "https://na.api.pvp.net/api/lol/na/v2.2/match/" + str(match["id"]) + \
                  "?includeTimeline=true&api_key=" + api_key

            response = urllib.urlopen(url)
            data = json.load(response)
            participant_id = -1
            for participant in data['participantIdentities']:
                if participant['player']['summonerId'] == self.id:
                    participant_id = participant['participantId']
            return data['timeline']['frames'], participant_id

    def get_build_from_match_index(self, match_index):
        """
        Get the item set for the match specified by it's index in the list.
        :param match_index: Int index of the match in the match list.
        :return: String with Item Set Json
        """
        timeline_data, participant_id = self.get_timeline_data(match_index)
        # generate a new item set from the events in the match
        item_set = ItemSet()
        for frame in timeline_data:
            try:
                events = frame['events']
                for event in events:
                    if event['eventType'] == 'ITEM_PURCHASED' and event['participantId'] == participant_id:
                        # print event
                        item_set.add_item(correct_item_id(event['itemId']), event['timestamp'])
                    if event['eventType'] == 'ITEM_UNDO' and event['participantId'] == participant_id:
                        # print event
                        # if the user undid a sell, then we should not undo the purchase
                        if event['itemBefore'] != 0:
                            item_set.undo_purchase()
                item_set.add_auto_block()
            except KeyError:
                pass
        return json.dumps(item_set.generate())


def correct_item_id(item_id):
    """
    Removes any non-shop item purchases, converting them to their shop equivalents
    :param item_id: Item id to check
    :return: Corresponding item id in shop
    """
    if item_id == 2010:
        # biscuits should be made potions, since they do not appear in the shop.
        return 2003
    else:
        return item_id


def get_champion_id(champion_name):
    """
    Get the champion ID from a champion's name.
    :param champion_name: String with champion's name.
    :return: String with champion id
    """
    return champion_data['data'][champion_name]['key']


def get_summoner_id(username):
    """
    Get the summoner from the API using the username.
    :param username: String with username to lookup.
    :return: Summoner object for the user.
    """
    url = "https://na.api.pvp.net/api/lol/na/v1.4/summoner/by-name/" + username + "?api_key=" + api_key
    response = urllib.urlopen(url)
    data = json.load(response)
    return Summoner(data[data.keys()[0]])


def main():
    summoner = get_summoner_id("musouka")
    summoner.get_matches(champion_name="Lulu")
    print summoner.get_build_from_match_index(5)


if __name__ == "__main__":
    main()