import datetime
import operator
import re

from game_assets import GameAssets


class U(str):
    def __format__(self, fmt):
        if fmt[0] == 'u':
            s = self.upper()
            fmt = fmt[1:]
        elif fmt[0] == 'l':
            s = self.lower()
            fmt = fmt[1:]
        else:
            s = str(self)
        return s.__format__(fmt)


class GameData:
    COLORS = ('blue', 'green', 'red', 'yellow', 'purple', 'brown')

    def __init__(self):
        self.EVENT_TYPES = {
            0: '[GUILD_WARS]',
            1: '[RAIDBOSS]',
            2: '[INVASION]',
            3: '[VAULT]',
            4: '[BOUNTY]',
            5: '[PETRESCUE]',
            6: '[CLASS_EVENT]',
            7: '[DELVE_EVENT]',
            8: '[TOWER_OF_DOOM]',
            9: '[HIJACK]',
            10: '[ADVENTURE_BOARD_SPECIAL_EVENT]',
            11: '[CAMPAIGN]',
        }
        self.data = None
        self.user_data = {
            'pEconomyModel': {
                'TroopReleaseDates': [],
                'KingdomReleaseDates': [],
                'HeroClassReleaseDates': [],
                'PetReleaseDates': [],
                'RoomReleaseDates': [],
                'WeaponReleaseDates': [],
                'BasicLiveEventArray': [],
            }
        }

        self.troops = {}
        self.spells = {}
        self.weapons = {}
        self.classes = {}
        self.banners = {}
        self.traits = {}
        self.kingdoms = {}
        self.pet_effects = ()
        self.pets = {}
        self.talent_trees = {}
        self.spoilers = []
        self.events = []
        self.soulforge_weapons = []
        self.campaign_tasks = {}
        self.campaign_data = {}

    @staticmethod
    def _convert_color_array(data_object):
        return [c.replace('Color', '').lower() for c, v in data_object['ManaColors'].items() if v]

    def read_json_data(self):
        self.data = GameAssets.load('World.json')
        self.user_data = GameAssets.load('User.json')
        if GameAssets.exists('Campaign.json'):
            self.campaign_data = GameAssets.load('Campaign.json')

    def populate_world_data(self):
        self.read_json_data()

        self.populate_spells()
        self.populate_traits()
        self.populate_troops()
        self.populate_kingdoms()
        self.populate_weapons()
        self.populate_pets()
        self.populate_talents()
        self.populate_classes()
        self.populate_release_dates()
        self.enrich_kingdoms()
        self.populate_campaign_tasks()

    def populate_classes(self):
        for _class in self.data['HeroClasses']:
            self.classes[_class['Id']] = {
                'id': _class['Id'],
                'name': _class['Name'],
                'code': _class['Code'],
                'talents': [self.talent_trees[tree]['talents'] for tree in _class['TalentTrees']],
                'trees': _class['TalentTrees'],
                'traits': [self.traits.get(trait, {'name': trait, 'description': '-'}) for trait in _class['Traits']],
                'weapon_id': _class['ClassWeaponId'],
                'kingdom_id': _class['KingdomId'],
                'type': _class['Augment'][0],
            }
            self.weapons[_class['ClassWeaponId']]['class'] = _class['Name']
            for tree in _class['TalentTrees']:
                self.talent_trees[tree]['classes'].append(self.classes[_class['Id']].copy())

    def populate_talents(self):
        for tree in self.data['TalentTrees']:
            talents = [self.traits.get(trait, trait) for trait in tree['Traits']]
            self.talent_trees[tree['Code']] = {
                'name': f'[TALENT_TREE_{tree["Code"].upper()}]',
                'talents': talents,
                'classes': [],
            }

    def populate_pets(self):
        self.pet_effects = (
            '[PETTYPE_BUFFTEAMCOLOR]',
            '[PETTYPE_BUFFGEMMASTERY]',
            '[PETTYPE_BUFFTEAMKINGDOM]',
            '[PETTYPE_BUFFTEAMTROOPTYPE]',
            '[PETTYPE_LOOTSOULS]',
            '[PETTYPE_LOOTGOLD]',
            '[PETTYPE_LOOTXP]',
            '[PETTYPE_NOEFFECT]',
        )
        for pet in self.data['Pets']:
            colors = self._convert_color_array(pet)
            self.pets[pet['Id']] = {
                'id': pet['Id'],
                'name': pet['Name'],
                'kingdom': self.kingdoms[pet['KingdomId']],
                'colors': sorted(colors),
                'effect': self.pet_effects[pet['Effect']],
                'effect_data': pet.get('EffectData'),
                'troop_type': pet.get('EffectTroopType'),
                'filename': pet['FileBase'],
            }

    def populate_weapons(self):
        for weapon in self.data['Weapons']:
            colors = self._convert_color_array(weapon)
            self.weapons[weapon['Id']] = {
                'id': weapon['Id'],
                'name': f'[SPELL{weapon["SpellId"]}_NAME]',
                'description': f'[SPELL{weapon["SpellId"]}_DESC]',
                'colors': sorted(colors),
                'rarity': weapon['WeaponRarity'],
                'type': weapon['Type'],
                'roles': weapon['TroopRoleArray'],
                'spell_id': weapon['SpellId'],
                'kingdom': self.kingdoms[weapon['KingdomId']],
                'requirement': weapon['MasteryRequirement'],
                'armor_increase': weapon['ArmorIncrease'],
                'attack_increase': weapon['AttackIncrease'],
                'health_increase': weapon['HealthIncrease'],
                'magic_increase': weapon['SpellPowerIncrease'],
                'affixes': [self.spells.get(spell) for spell in weapon['Affixes'] if spell in self.spells],
            }

    def populate_kingdoms(self):
        for kingdom in self.data['Kingdoms']:
            colors = [f'[GEM_{c.upper()}]' for c in self.COLORS]
            colors = zip(colors, kingdom['BannerColors'])
            colors = sorted(colors, key=operator.itemgetter(1), reverse=True)
            self.banners[kingdom['Id']] = {
                'name': kingdom['BannerName'],
                'colors': colors,
                'filename': kingdom['FileBase'],
            }
            kingdom_troops = [troop_id for troop_id in kingdom['TroopIds'] if troop_id != -1]
            kingdom_colors = self._convert_color_array(kingdom)
            self.kingdoms[kingdom['Id']] = {
                'id': kingdom['Id'],
                'name': kingdom['Name'],
                'description': kingdom['Description'],
                'punchline': kingdom['ByLine'],
                'underworld': bool(kingdom.get('MapIndex', 0)),
                'troop_ids': kingdom_troops,
                'troop_type': kingdom['KingdomTroopType'],
                'linked_kingdom_id': kingdom.get('SisterKingdomId'),
                'colors': sorted(kingdom_colors),
                'filename': kingdom['FileBase'],
            }
            if 'SisterKingdomId' in kingdom:
                self.kingdoms[kingdom['SisterKingdomId']]['linked_kingdom_id'] = kingdom['Id']
            for troop_id in kingdom_troops:
                self.troops[troop_id]['kingdom'] = kingdom

    def populate_troops(self):
        for troop in self.data['Troops']:
            colors = self._convert_color_array(troop)
            self.troops[troop['Id']] = {
                'id': troop['Id'],
                'name': troop['Name'],
                'colors': sorted(colors),
                'description': troop['Description'],
                'spell_id': troop['SpellId'],
                'traits': [self.traits.get(trait, {'name': trait, 'description': '-'}) for trait in troop['Traits']],
                'rarity': troop['TroopRarity'],
                'types': [troop['TroopType']],
                'roles': troop['TroopRoleArray'],
                'kingdom': {'Name': ''},
                'filename': troop["FileBase"],
            }
            if 'TroopType2' in troop:
                self.troops[troop['Id']]['types'].append(troop['TroopType2'])

    def populate_traits(self):
        for trait in self.data['Traits']:
            self.traits[trait['Code']] = {'name': trait['Name'], 'description': trait['Description']}

    def populate_spells(self):
        for spell in self.data['Spells']:
            spell_effects = []
            boost = 0
            last_type = ""
            for step in spell['SpellSteps']:
                if 'Type' in step and 'SpellPowerMultiplier' in step:
                    amount = step.get('Amount', 0)
                    multiplier = step.get('SpellPowerMultiplier', 1)
                    if last_type != step['Type']:
                        spell_effects.append([multiplier, amount])
                        last_type = step['Type']
                elif step['Type'].startswith('Count'):
                    boost = step.get('Amount', 1)
            self.spells[spell['Id']] = {
                'id': spell['Id'],
                'name': spell['Name'],
                'description': spell['Description'],
                'cost': spell['Cost'],
                'effects': spell_effects,
                'boost': boost,
            }

    def get_current_event_kingdom(self):
        today = datetime.date.today()
        world_event = [e for e in self.events
                       if e['end'] - e['start'] == datetime.timedelta(days=7)
                       and e['start'] <= today <= e['end']
                       and e['kingdom_id']][0]
        event_kingdom_id = world_event['kingdom_id']
        return event_kingdom_id

    def populate_campaign_tasks(self):
        event_kingdom_id = self.get_current_event_kingdom()

        tasks = self.user_data['pTasksData']['CampaignTasks'][str(event_kingdom_id)]
        for level in ('Bronze', 'Silver', 'Gold'):
            task_list = [self.transform_campaign_task(task) for task in tasks[level]]
            self.campaign_tasks[level.lower()] = sorted(task_list, key=operator.itemgetter('order'))

    def transform_campaign_task(self, task):
        extra_data = {}
        m = re.match(r'Campaign_(?P<kingdom_id>\d+)_(?P<level>.+)_(?P<order>\d+)', task['Id'])
        task_id = m.groupdict()
        task_order = int(task_id['order'])
        kingdom_id = task_id['kingdom_id']
        level = task_id['level']

        for i, t in enumerate(self.campaign_data.get(f'Campaign{level}', [])):
            if t['Id'] == task['Id']:
                extra_data = t
                task_order = i

        translated_task = {
            'reward': task['Rewards'][0]['Amount'],
            'condition': task.get('Condition'),
            'order': task_order,
            'task': task['Task'],
            'name': task['TaskName'],
            'title': task['TaskTitle'],
            'tags': task['Tag'].split(','),
            'x': task.get('XValue'),
            'y': task.get('YValue'),
            'value0': U(extra_data.get('Value0', '`?`')),
            'value1': U(extra_data.get('Value1', '`?`')),
            'c': U(task.get('CValue')),
            'd': U(task.get('DValue')),
            'kingdom_id': int(kingdom_id),
            'orig': task,
        }

        return translated_task

    @staticmethod
    def get_datetime(val):
        date_format = '%m/%d/%Y %I:%M:%S %p %Z'
        return datetime.datetime.strptime(val, date_format)

    def populate_release_dates(self):
        release: dict
        for release in self.user_data['pEconomyModel']['TroopReleaseDates']:
            troop_id = release['TroopId']
            release_date = self.get_datetime(release['Date'])
            if troop_id in self.troops:
                self.troops[troop_id]['release_date'] = release_date
                self.spoilers.append({'type': 'troop', 'date': release_date, 'id': troop_id})
        for release in self.user_data['pEconomyModel']['PetReleaseDates']:
            pet_id = release['PetId']
            release_date = self.get_datetime(release['Date'])
            if pet_id in self.pets:
                self.pets[pet_id]['release_date'] = release_date
                self.spoilers.append({'type': 'pet', 'date': release_date, 'id': pet_id})
        for release in self.user_data['pEconomyModel']['KingdomReleaseDates']:
            kingdom_id = release['KingdomId']
            release_date = self.get_datetime(release['Date'])
            if kingdom_id in self.kingdoms:
                self.kingdoms[kingdom_id]['release_date'] = release_date
                self.spoilers.append({'type': 'kingdom', 'date': release_date, 'id': kingdom_id})
        for release in self.user_data['pEconomyModel']['HeroClassReleaseDates']:
            class_id = release['QuestId']
            release_date = self.get_datetime(release['Date'])
            if class_id in self.classes:
                self.classes[class_id]['release_date'] = release_date
                self.spoilers.append({'type': 'class', 'date': release_date, 'id': class_id})
        for release in self.user_data['pEconomyModel']['RoomReleaseDates']:
            room_id = release['RoomId']
            release_date = self.get_datetime(release['Date'])
            # self.rooms[room_id]['release_date'] = release_date
            self.spoilers.append({'type': 'room', 'date': release_date, 'id': room_id})
        for release in self.user_data['pEconomyModel']['WeaponReleaseDates']:
            weapon_id = release['WeaponId']
            release_date = self.get_datetime(release['Date'])
            if weapon_id in self.weapons:
                self.weapons[weapon_id]['release_date'] = release_date
                self.spoilers.append({'type': 'weapon', 'date': release_date, 'id': weapon_id})
        for release in self.user_data['BasicLiveEventArray']:
            result = {'start': datetime.datetime.utcfromtimestamp(release['StartDate']).date(),
                      'end': datetime.datetime.utcfromtimestamp(release['EndDate']).date(),
                      # 'id': release['Id'],
                      'type': self.EVENT_TYPES.get(release['Type'], release['Type']),
                      'names': release.get('Name'),
                      'gacha': release['GachaTroop'],
                      'kingdom_id': release.get('Kingdom')}
            self.events.append(result)

        week_long_events = [e for e in self.events
                            if e['end'] - e['start'] == datetime.timedelta(days=7)
                            and e['kingdom_id']]
        non_craftable_wepon_ids = [
            1102, 1114, 1070, 1073, 1119, 1118, 1108, 1109, 1203, 1092, 1067, 1094, 1179, 1178, 1069, 1127, 1096, 1134,
            1097, 1103, 1115, 1123, 1120, 1071, 1095, 1072, 1107, 1100, 1106, 1213, 1121, 1093, 1122, 1295, 1250, 1317,
            1294, 1239, 1223, 1222, 1272, 1252, 1287, 1275, 1251, 1238, 1224, 1296, 1273, 1274, 1286, 1225
        ]
        for event in week_long_events:
            # print([w['kingdom']['id'] for w in self.weapons.values()])
            kingdom_weapons = [w['id'] for w in self.weapons.values()
                               if 'kingdom' in w and w['kingdom']['id'] == event['kingdom_id']
                               and w['id'] not in non_craftable_wepon_ids
                               and w.get('release_date', datetime.datetime.min).date() < event['end']]
            self.soulforge_weapons.append({
                'start': event['start'],
                'end': event['end'],
                'weapon_ids': kingdom_weapons,
            })

        self.events.sort(key=operator.itemgetter('start'))
        self.spoilers.sort(key=operator.itemgetter('date'))

    def enrich_kingdoms(self):
        for kingdom_id, kingdom_data in self.user_data['pEconomyModel']['KingdomLevelData'].items():
            self.kingdoms[int(kingdom_id)]['primary_color'] = self.COLORS[kingdom_data['Color']]
            self.kingdoms[int(kingdom_id)]['primary_stat'] = kingdom_data['Stat']

        for kingdom_id, pet_id in self.user_data['pEconomyModel']['FactionRenownRewardPetIds'].items():
            self.kingdoms[int(kingdom_id)]['pet'] = self.pets[pet_id]
