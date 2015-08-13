__author__ = 'hetoan2'

import urllib
import json
import datetime

api_key_file = open("api_key.txt", "r")
api_key = api_key_file.read().replace('\n', '')
print "Using api key: " + api_key

class ItemSet(object):
    def __init__(self):
        self.title = "Generated Item Set"
        self.type = "custom"
        self.map = "any"
        self.mode = "any"
        self.priority = False
        self.sortrank = 5
        self.blocks = list()
        self.auto_block = Block()
        self.last_timestamp = 0

    def add_block(self, block):
        """
        Add a block to the list of blocks
        :param block: The block of items to add
        :return:
        """
        self.blocks.append(block)

    def add_item(self, item_id, timestamp):
        # automatically add our block if it's a new back time
        if timestamp - self.last_timestamp > 2000 and timestamp < 1300000 and not self.auto_block.is_empty():
            self.add_auto_block()

        self.auto_block.add_item(item_id)
        self.last_timestamp = timestamp

    def remove_item(self, item_id, timestamp):
        self.auto_block.remove_item(item_id)
        self.last_timestamp = timestamp

    def undo_purchase(self):
        self.auto_block = Block()

    def add_auto_block(self):
        """
        Automatically Generated blocks based off timestamp information will use this method to add blocks to the list
        :return:
        """
        time = datetime.timedelta(milliseconds=self.last_timestamp)
        minutes, seconds = divmod(time.seconds, 60)
        self.auto_block.type = "%02d:%02d" % (minutes, seconds)
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
        for item in self.items:
            if item["id"] == str(item_id):
                if item["count"] == 1:
                    self.items.remove(item)
                else:
                    item["count"] -= 1

    def is_empty(self):
        return len(self.items) == 0

    def generate(self):
        """
        Generate the json object for this class
        :return:
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

    def get_matches(self, champion_id=None, soloq=False):
        if champion_id is None:
            url = "https://na.api.pvp.net/api/lol/na/v2.2/matchhistory/" + str(self.id)
            if soloq:
                url += "?rankedQueues=RANKED_SOLO_5x5&api_key=" + api_key
            else:
                url += "?api_key=" + api_key
        else:
            url = ""

        # get the response from the server
        response = urllib.urlopen(url)
        data = json.load(response)
        self.matches = [match_id['matchId'] for match_id in data['matches']]
        # for match in data['matches']:
        #     print match['participants']
        self.participant_ids = []
        print self.matches

    def get_timeline_data(self, match_index):
        if len(self.matches) != 0:
            match = self.matches[match_index]
            url = "https://na.api.pvp.net/api/lol/na/v2.2/match/" + str(match) + \
                  "?includeTimeline=true&api_key=" + api_key

            response = urllib.urlopen(url)
            data = json.load(response)
            for participant in data['participantIdentities']:
                if participant['player']['summonerId'] == self.id:
                    self.participant_id = participant['participantId']
            return data['timeline']['frames']


def correct_item_id(item_id):
    """
    Removes any non-shop item purchases, converting them to their shop equivalents
    :param item_id: Item id to check
    :return: Corresponding item in shop
    """
    if item_id == 2010:
        return 2003
    else:
        return item_id


def get_summoner_id(username):
    url = "https://na.api.pvp.net/api/lol/na/v1.4/summoner/by-name/" + username + "?api_key=" + api_key
    response = urllib.urlopen(url)
    data = json.load(response)
    return Summoner(data[username])


def main():
    summoner = get_summoner_id("musouka")
    summoner.get_matches(soloq=True)
    tdata = summoner.get_timeline_data(5)
    item_set = ItemSet()
    for frame in tdata:
        try:
            events = frame['events']
            for event in events:
                if event['eventType'] == 'ITEM_PURCHASED' and event['participantId'] == summoner.participant_id:
                    print event
                    item_set.add_item(correct_item_id(event['itemId']), event['timestamp'])
                if event['eventType'] == 'ITEM_UNDO' and event['participantId'] == summoner.participant_id:
                    print event
                    # item_set.remove_item(correct_item_id(event['itemId']), event['timestamp'])
                    item_set.undo_purchase()
            item_set.add_auto_block()
        except KeyError:
            pass
    print json.dumps(item_set.generate())


if __name__ == "__main__":
    main()