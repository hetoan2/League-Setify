from django.db import models
import urllib
import json
import datetime

api_key = ""

dd_version = json.load(urllib.urlopen("https://global.api.pvp.net/api/lol/static-data/na/v1.2/versions"
                                      "?api_key=" + api_key))[0]

# print "Using DataDragon version: " + dd_version

champion_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com"
                                         "/cdn/" + dd_version + "/data/en_US/champion.json"))

item_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com/cdn/" + dd_version + "/data/en_US/item.json"))

summoner_spell_data = json.load(urllib.urlopen("http://ddragon.leagueoflegends.com"
                                               "/cdn/" + dd_version + "/data/en_US/summoner.json"))


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
        self.sortrank = 0
        self.blocks = list()
        self.auto_block = Block()
        self.back_number = 0
        self.done_auto_blocks = False
        self.last_timestamp = 0

        if include_consumables:
            consumable_block = Block()
            consumable_block.type = "Consumables"
            for item in item_data['data']:
                # could exclude non-purchasable items, but the exclusion for consumable is done in add_item check
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
        if timestamp is not None:
            if timestamp - self.last_timestamp > 60000:
                # this triggers on the each back (assuming they don't take over a minute to do purchases)
                self.back_number += 1

            # first block is for starting items & first back
            if self.back_number == 2 and timestamp - self.last_timestamp > 60000:
                self.auto_block.type = "Starting Items & First Back"
                self.add_auto_block()

            # save timestamp for monitoring
            self.last_timestamp = timestamp

            if self.back_number == 3:
                time = datetime.timedelta(milliseconds=timestamp)
                minutes, seconds = divmod(time.seconds, 60)
                self.auto_block.type = ("Second Back [%02d:%02d]" % (minutes, seconds)) + " - Midgame"

            # second block is for second back to midgame [20:00]
            if timestamp > 1200000 and not self.done_auto_blocks:
                self.add_auto_block()
                # third block is for anything purchased after, establish the name here
                self.auto_block.type = "Lategame"
                self.done_auto_blocks = True


        self.auto_block.add_item(item_id)

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
        self.auto_block.type += " [%02d:%02d]" % (minutes, seconds)
        # self.auto_block.type = "%02d:%02d        |           |   |" % (minutes, seconds)
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

    def add_item(self, item_id, stacks=False):
        """
        Add an item to the block, automatically grouping quantities of identical items
        :param item_id: The item id to add to the block
        :return:
        """
        item_id = correct_item_id(int(item_id))
        # do not attempt to add empty slots
        if item_id == 0:
            return
        if stacks:
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


def correct_item_id(item_id):
    """
    Removes any non-shop item purchases, converting them to their shop equivalents
    :param item_id: Item id to check
    :return: Corresponding item id in shop
    """
    if item_id == 2010:
        # biscuits should be made potions, since they do not appear in the shop.
        return 2003
    elif item_id == 2050:
        return 0
    else:
        return item_id


def get_timeline_data(region, match_id, user_id):
        url = "https://" + str(region) + ".api.pvp.net/api/lol/" + str(region) + "/v2.2/match/" + str(match_id) + \
              "?includeTimeline=true&api_key=" + api_key

        response = urllib.urlopen(url)
        data = json.load(response)
        participant_id = -1
        for participant in data['participantIdentities']:
            if str(participant['player']['summonerId']) == str(user_id):
                participant_id = participant['participantId']

        final_build = list()

        # participant id is 1 indexed, so subtract 1, getting the participant's stats for final build
        stats = data['participants'][int(participant_id)-1]['stats']
        final_build.append(stats['item0'])
        final_build.append(stats['item1'])
        final_build.append(stats['item2'])
        final_build.append(stats['item3'])
        final_build.append(stats['item4'])
        final_build.append(stats['item5'])
        final_build.append(stats['item6'])

        return data['timeline']['frames'], participant_id, final_build


def get_build_from_match_id(region, match_id, user_id):
    """
    Get the item set for the match specified.
    :param match_id: Int containing the match ID.
    :return: ItemSet
    """
    timeline_data, participant_id, final_build = get_timeline_data(region, match_id, user_id)
    # generate a new item set from the events in the match
    item_set = ItemSet()
    for frame in timeline_data:
        try:
            events = frame['events']
            for event in events:
                if event['eventType'] == 'ITEM_PURCHASED' and event['participantId'] == participant_id:
                    item_set.add_item(event['itemId'], event['timestamp'])
                if event['eventType'] == 'ITEM_UNDO' and event['participantId'] == participant_id:
                    # if the user undid a sell, then we should not undo the purchase
                    if event['itemBefore'] != 0:
                        item_set.undo_purchase()
        except KeyError:
            pass

    # if the game ends very early there is a chance the name will not be set, in these circumstances
    # we should name the last block accordingly.
    if item_set.auto_block.type == "Block Title":
        item_set.auto_block.type = "Last Purchase"

    item_set.add_auto_block()
    final_build_block = Block()
    final_build_block.type = "Full Build"
    for item in final_build:
        final_build_block.add_item(item)
    item_set.add_block(final_build_block)

    return item_set