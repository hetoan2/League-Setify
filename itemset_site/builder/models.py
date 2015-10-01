# from django.db import models
from django.core.cache import cache
from time import sleep
import urllib
import json
import datetime
import operator

api_key = ""

dd_version = cache.get('version')


def get_version():
    global versions, dd_version
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
get_version()


# static data CDN calls don't need to be rate limited
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

        self.summoners_rift = True

        if include_consumables:
            consumable_block = Block()
            consumable_block.type = "Consumables"
            for item in item_data['data']:
                # could exclude non-purchasable items, but the exclusion for consumable is done in add_item check
                if 'Consumable' in item_data['data'][item]['tags']:
                    consumable_block.add_item(item)
            # sort the consumable block
            consumable_block.sort()
            # manually add three trinkets to the end
            consumable_block.add_item(3340)
            consumable_block.add_item(3341)
            consumable_block.add_item(3342)
            self.blocks.append(consumable_block)

    def add_block(self, block):
        """
        Add a block to the list of blocks, only if it is not empty.
        :param block: The block of items to add
        :return:
        """
        if not block.is_empty():
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

    def undo_purchase(self, before_item):
        """
        Remove the item that was purchased.
        :return:
        """
        self.auto_block.remove_item(before_item)

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
        self.last_item = 0

    def add_item(self, item_id, stacks=False, unique=False):
        """
        Add an item to the block, automatically grouping quantities of identical items
        :param item_id: The item id to add to the block
        :param stacks: If true, items already in the block will stack.
        :param unique: If true, the item may only appear in the block once, and will not stack.
        :return:
        """
        item_id = correct_item_id(int(item_id))
        # do not attempt to add empty slots
        if item_id == 0:
            return
        # add item and ensure it does not already exist in block
        if unique:
            for item in self.items:
                # found item, and already in list
                if item["id"] == str(item_id):
                    return
        # add item, stacking items of same type
        if stacks:
            for item in self.items:
                if item["id"] == str(item_id):
                    item["count"] += 1
                    return
        # default, item not in list (or we aren't stacking), so add it
        self.items.append({"id": str(item_id), "count": 1})

    def add_item_from_form(self, item_id):
        # if last item added from form is the same as this item, group them together (add to count of previous)
        if self.last_item == item_id:
            self.items[-1]['count'] += 1
        # otherwise, add a new slot for the item
        else:
            self.items.append({"id": str(item_id), "count": 1})

        # store what the last item was
        self.last_item = item_id

    def remove_item(self, item_id):
        """
        Remove a single item from the block, if multiples exist, will decrement the number in the block.
        :param item_id: Item id to remove (one of) from the block.
        :return:
        """
        for item in self.items:
            if item["id"] == str(item_id):
                print "removed 1 "+str(item_id)
                if item["count"] == 1:
                    self.items.remove(item)
                else:
                    item["count"] -= 1
                return

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
        try:
            self.items = sorted(self.items, key=lambda item: item_data['data'][item["id"]]['gold']['total'])
        # an item id is in here that is no longer in the latest version. remove it and try again.
        except KeyError as bad_item_id:
            self.remove_item(bad_item_id[0])
            self.sort()

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
    def __init__(self, summoner_object, region="na"):
        self.id = summoner_object['id']
        self.name = summoner_object['name']
        self.matches = list()
        self.participant_ids = list()
        self.participant_id = 0
        self.version = dd_version
        self.region = region

    def get_matches(self, champion_name=None, ranked=None, timelinedata=False):
        """
        Get a list of match IDs for this summoner
        :param champion_name: String containing the champion name to filter games for
        :param ranked: Boolean on whether to restrict to soloq games or not.
        :return:
        """
        global versions

        query_params = {}
        url = "https://" + self.region + ".api.pvp.net/api/lol/" + self.region + "/v2.2/matchlist/by-summoner/" + str(self.id) + "?"

        if ranked == 1:
            query_params['rankedQueues'] = 'RANKED_SOLO_5x5'
        elif ranked == 2:
            query_params['rankedQueues'] = 'RANKED_TEAM_3x3'
        elif ranked == 3:
            query_params['rankedQueues'] = 'RANKED_TEAM_5x5'

        # query_params['beginIndex'] = 10
        # query_params['endIndex'] = 100

        champion_id = None
        if champion_name is not None:
            champion_id = get_champion_id(champion_name)
            print champion_id
            query_params['championIds'] = champion_id

        query_params['api_key'] = api_key

        # add the query parameters to the url
        url += urllib.urlencode(query_params)

        print url

        # get the response from the server
        data = fetch_json_from_url(url)

        # print data

        try:
            self.matches = list()

            count = 0
            for match in data['matches']:
                count += 1
                if count >= 10:
                    break

                match_id = match["matchId"]

                url = "https://" + self.region + ".api.pvp.net/api/lol/" + self.region + "/v2.2/match/" + str(match_id) + "?"
                if timelinedata:
                    url += "includeTimeline=true&"
                url += "api_key=" + api_key

                _match = fetch_json_from_url(url)

                participant = 0

                for p in _match['participantIdentities']:
                    # print "p:", p
                    if p['player']['summonerId'] == self.id:
                        participant = p['participantId'] - 1

                stats = _match['participants'][participant]['stats']
                # print stats
                match_data = {"id": _match['matchId'],
                              "champ": get_champion_name(_match['participants'][participant]['championId']),
                              "score": "%s/%s/%s" % (stats['kills'], stats['deaths'], stats['assists']),
                              "gold": '{:.1f}'.format(float(stats['goldEarned']) / 1000) + "k",
                              "spell_1": get_summoner_spell_image(_match['participants'][participant]['spell1Id']),
                              "spell_2": get_summoner_spell_image(_match['participants'][participant]['spell2Id']),
                              # for version, replace find second decimal place (replace first decimal with space,
                              # then do find on result to get index of second decimal, strip to base version
                              # finally adding ".1" to end of version number to get the data dragon variant.
                              "version": _match['matchVersion']
                                         [:_match['matchVersion'].replace(".", " ", 1).find(".")] + ".1",
                              "status": stats['winner'],
                              "date": datetime.datetime.fromtimestamp(_match['matchCreation'] // 1000).strftime("%x"),
                              }

                try:
                    # validate if version is in version list (some patches don't have .1 as their base version)
                    while match_data["version"] not in versions:
                        # if it isn't, strip the end off and increment
                        oldversion = int(match_data["version"][-1:])
                        match_data["version"] = match_data["version"][:-1]+str(oldversion+1)
                        # let's not make our server stuck with some anomaly in the data... only iterate this 5 times maximum
                        if oldversion > 5:
                            break
                except NameError:
                    get_version()

                item_slots = ['0', '1', '2', '3', '4', '5', '6']
                for slot in item_slots:
                    if stats['item' + slot] != 0:
                        # print stats['item'+slot]
                        match_data[slot] = stats['item' + slot]
                # print match_data
                self.matches.append(match_data)
        except KeyError:
            # if there are no matches, create a blank list.
            self.matches = []

        self.participant_ids = []

        return True

    def get_build_from_matches(self):
        """
        Generate a build from the current list of matches
        :return: ItemSet
        """
        item_set = ItemSet()

        items_won = {}
        items_loss = {}

        # the following 3 variables could be used to improve this algorithm in the future.
        sample_size = len(self.matches)
        num_wins = 0
        num_loss = 0

        item_slots = ['0', '1', '2', '3', '4', '5', '6']
        for match in self.matches:
            weight = 1
            if match["version"] != dd_version:
                # give less weight to old patches
                weight = 0.5

            # if match was won, load items weight into items_won
            if match["status"]:
                items = items_won
                num_wins += 1
            else:
                items = items_loss
                num_loss += 1

            # add all non-empty slots to the items dictionary
            for slot in item_slots:
                try:
                    if str(match[slot]) in items:
                        items[str(match[slot])] += weight
                    else:
                        items[str(match[slot])] = weight
                # if item slot is empty there will not be a key for it
                except KeyError:
                    pass

        items_general = {}

        delete_ids = list()

        # separate items won & items loss, putting items in both into a general category
        for item in items_won:
            if item in items_loss:
                items_general[item] = items_won[item] + items_loss[item]
                delete_ids.append(item)

        # delete all the items that were moved to general
        for item in delete_ids:
            try:
                # remove common items from the other categories
                del items_won[item]
                del items_loss[item]
            except KeyError:
                pass

        # get a list of tuples with item ids and their weight in descending (higher weight first)
        win_items_ordered = sorted(items_won.items(), key=operator.itemgetter(1))[::-1]
        lose_items_ordered = sorted(items_loss.items(), key=operator.itemgetter(1))[::-1]
        general_items_ordered = sorted(items_general.items(), key=operator.itemgetter(1))[::-1]

        # all items
        all_items = items_general.copy()
        all_items.update(items_won)
        all_items.update(items_loss)

        # order all the items for the final items
        final_items_ordered = sorted(all_items.items(), key=operator.itemgetter(1))[::-1]

        # consumable block (in itemset by default)
        # t1 component block
        base_components = Block()
        base_components.type = "Core Components"
        # t2 component block
        adv_components = Block()
        adv_components.type = "Secondary Components"
        # ? essential items
        core_items = Block()
        core_items.type = "Essential Items"
        # winning items
        win_items = Block()
        win_items.type = "Ahead Items"
        # losing items
        behind_items = Block()
        behind_items.type = "Behind Items"
        # final build
        final_items = Block()
        final_items.type = "Example Final Build"

        # first, generate a list of all the components that the items built come from
        for item in general_items_ordered + win_items_ordered + lose_items_ordered:
            # get the item id from the list (first element of tuple)
            item_id = item[0]
            # the second element in tuple is the weight, but we only needed that for sorting.

            try:
                from_items = item_data['data'][item_id]['from']
                for from_item_id in from_items:
                    try:
                        # this will throw a KeyError if the from_item_id is a base component
                        assert item_data['data'][from_item_id]['from']
                        # it passed, so the from component must be a tier 2 component
                        adv_components.add_item(from_item_id, stacks=False, unique=True)
                    except KeyError:
                        base_components.add_item(from_item_id, stacks=False, unique=True)
            # tier 1 components will have no "from" attribute (they build from nothing) and throw KeyError1
            except KeyError:
                base_components.add_item(item_id, stacks=False, unique=True)

        for item in general_items_ordered:
            try:
                # make sure the item is at least tier 2 (do not show core components in outside their block)
                assert item_data['data'][item[0]]['from']
                core_items.add_item(item[0], stacks=False, unique=True)
            except KeyError:
                pass

        for item in win_items_ordered:
            try:
                # make sure the item is at least tier 2 (do not show core components in outside their block)
                assert item_data['data'][item[0]]['from']
                win_items.add_item(item[0], stacks=False, unique=True)
            except KeyError:
                pass

        for item in lose_items_ordered:
            try:
                # make sure the item is at least tier 2 (do not show core components in outside their block)
                assert item_data['data'][item[0]]['from']
                behind_items.add_item(item[0], stacks=False, unique=True)
            except KeyError:
                pass

        final_items_count = 0
        has_boots = False
        has_jungle_item = False
        has_gold_item = False

        print final_items_ordered
        for item in final_items_ordered:
            if final_items_count >= 6:
                break
            try:
                # make sure the item is at least tier 2 (do not show core components in outside their block)
                assert item_data['data'][item[0]]['from']

                # only put one pair of boots into final build
                if 'Boots' in item_data['data'][item[0]]['tags']:
                    if has_boots:
                        continue
                    else:
                        has_boots = True

                # only put one jungle item into final build
                if 'Jungle' in item_data['data'][item[0]]['tags']:
                    if has_jungle_item:
                        continue
                    else:
                        has_jungle_item = True

                # only put one gold item into final build
                if 'GoldPer' in item_data['data'][item[0]]['tags']:
                    if has_gold_item:
                        continue
                    else:
                        has_gold_item = True

                # make sure the item is not a trinket first
                if 'Trinket' not in item_data['data'][item[0]]['tags']:
                    add_item = True
                    try:
                        # check to make sure this item doesn't build into an item already in the final build
                        for item_id in item_data['data'][item[0]]['into']:
                            # build into item was found in final items.
                            if item_id in [f_item[0] for f_item in final_items_ordered]:
                                add_item = False
                    # KeyError means that this item does not build into anything else
                    except KeyError:
                        pass
                    # if item is still good to add, add it.
                    if add_item:
                        final_items.add_item(item[0], stacks=False, unique=True)
                        final_items_count += 1
                else:
                    raise KeyError
            except KeyError:
                continue

        # sort the base components by price
        base_components.sort()
        item_set.add_block(base_components)
        item_set.add_block(adv_components)
        item_set.add_block(core_items)
        item_set.add_block(win_items)
        item_set.add_block(behind_items)
        item_set.add_block(final_items)

        return item_set


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

    data = fetch_json_from_url(url)

    participant_id = -1
    for participant in data['participantIdentities']:
        if str(participant['player']['summonerId']) == str(user_id):
            participant_id = participant['participantId']

    runes = data['participants'][int(participant_id) - 1]['runes']
    masteries = data['participants'][int(participant_id) - 1]['masteries']

    runes_masteries = (runes, masteries)

    final_build = list()

    # participant id is 1 indexed, so subtract 1, getting the participant's stats for final build
    stats = data['participants'][int(participant_id) - 1]['stats']
    final_build.append(stats['item0'])
    final_build.append(stats['item1'])
    final_build.append(stats['item2'])
    final_build.append(stats['item3'])
    final_build.append(stats['item4'])
    final_build.append(stats['item5'])
    final_build.append(stats['item6'])

    champion_name = get_champion_name(data['participants'][int(participant_id) - 1]['championId'])
    map_id = data['mapId']

    participant_info = (participant_id, champion_name, map_id)

    return data['timeline']['frames'], participant_info, final_build, runes_masteries


def get_name_from_user_id(region, user_id):
    url = 'https://' + str(region) + '.api.pvp.net/api/lol/' + str(region) + '/v1.4/summoner/' \
          + str(user_id) + '/name?api_key=' + api_key

    try:
        data = fetch_json_from_url(url)
        return data[str(user_id)]
    except ValueError:
        return ""


def get_build_from_match_id(region, match_id, user_id):
    """
    Get the item set for the match specified.
    :param match_id: Int containing the match ID.
    :return: ItemSet
    """
    timeline_data, participant_info, final_build, runes_masteries = get_timeline_data(region, match_id, user_id)

    # if the timeline is none, there was an error fetching from the server, should display error page
    if timeline_data is None:
        return None

    participant_id, champion_name, map_id = participant_info

    participant_name = get_name_from_user_id(region, user_id)

    itemset_name = ""

    if participant_name != "":
        itemset_name += participant_name + "'s "

    itemset_name += champion_name

    # generate a new item set from the events in the match
    item_set = ItemSet()
    item_set.title = itemset_name
    item_set.champion = champion_name

    # set the summoner's rift flag to false if on twisted treeline (other modes not be reported as they are not ranked)
    if map_id == 10:
        item_set.summoners_rift = False

    for frame in timeline_data:
        try:
            events = frame['events']
            for event in events:
                if event['eventType'] == 'ITEM_PURCHASED' and event['participantId'] == participant_id:
                    item_set.add_item(event['itemId'], event['timestamp'])
                    print event
                elif event['eventType'] == 'ITEM_UNDO' and event['participantId'] == participant_id:
                    print event
                    # if the user undid a sell, then we should not undo the purchase
                    if event['itemBefore'] != 0:
                        item_set.undo_purchase(event['itemBefore'])
        except KeyError:
            pass

    # if the game ends very early there is a chance the name will not be set, in these circumstances
    # we should name the last block accordingly.
    if item_set.auto_block.type == "Block Title":
        item_set.auto_block.type = "Last Purchase"

    item_set.add_auto_block()
    final_build_block = Block()
    final_build_block.type = "Full Build"
    if final_build is not None:
        for item in final_build:
            final_build_block.add_item(item)
    item_set.add_block(final_build_block)

    return item_set, runes_masteries


def get_summoner_id(username, region="na"):
    """
    Get the summoner from the API using the username.
    :param username: String with username to lookup.
    :param region: String with region to lookup in.
    :return: Summoner object for the user.
    """
    url = "https://" + region + ".api.pvp.net/api/lol/" + region + "/v1.4/summoner/by-name/" + username + "?api_key=" + api_key
    data = fetch_json_from_url(url)
    return Summoner(data[data.keys()[0]], region=region)


def get_champion_id(champion_name):
    """
    Get the champion ID from a champion's name.
    :param champion_name: String with champion's name.
    :return: String with champion id
    """
    return champion_data['data'][champion_name]['key']


def get_champion_name(champion_id):
    """
    Get the champion's name from it's ID
    :param champion_id: Champion key.
    :return: String with champion name.
    """
    for champ in champion_data['data']:
        if champion_data['data'][champ]['key'] == str(champion_id):
            return champ


def get_summoner_spell_image(spell_id):
    """
    Get the summoner key name (used for image) from ID.
    :param spell_id:
    :return: Summoner spell key name
    """
    for spell in summoner_spell_data['data']:
        if summoner_spell_data['data'][spell]['key'] == str(spell_id):
            return spell
    return "SummonerFlash"


request_count = 0
last_request = None


def fetch_json_from_url(url, tries=0):
    """
    Load JSON from URL, if there is an error, try again. Rate limiting is done in here.
    :param url: URL to open
    :return: JSON object
    """
    global request_count, last_request

    # we are not getting stuck here. only try 5 times.
    if tries > 5:
        raise LookupError

    try:
        if last_request is None:
            last_request = datetime.datetime.now()
        # if it has been less than 10 seconds
        if (datetime.datetime.now() - last_request).total_seconds() < 10:
            if request_count > 10:
                # if we have made more than 10 calls in past 10 seconds, wait and try again
                sleep(0.5)
                return fetch_json_from_url(url, tries=tries+1)
        else:
            # reset our counters
            request_count = 0
            last_request = datetime.datetime.now()

        response = urllib.urlopen(url.encode("UTF-8"))
        data = json.load(response)

        try:
            # search for a rate limit error
            if data['status']['status_code'] == 429:
                # if found, we should read the retry-after header and sleep, provided we aren't hanging for 20 seconds.
                sleep_time = int(response.info()['Retry-After'])
                if sleep_time < 10:
                    sleep(sleep_time)
                    return fetch_json_from_url(url, tries=tries+1)
                else:
                    raise LookupError
        except KeyError:
            pass

        # increment a request when valid data was received
        request_count += 1
        return data
    # value error means we did not get valid JSON back, so retry.
    except ValueError:
        return fetch_json_from_url(url, tries=tries+1)
