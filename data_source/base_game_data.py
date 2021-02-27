import copy

import translations
from util import dig, extract_search_tag

_ = translations.Translations().get


class BaseGameData:
    def __init__(self, data):
        self.data = data

    def set_release_date(self, release_date):
        self.data['release_date'] = release_date

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __contains__(self, item):
        return item in self.data

    def __getattr__(self, item):
        return self.data[item]


class BaseGameDataContainer:
    DATA_CLASS = None
    LOOKUP_KEYS = []

    def __init__(self):
        self.data = {}
        self.translations = {}

    def translate_one_language(self, lang):
        item = copy.deepcopy(self.data)
        self.deep_translate(item, lang)
        if self.is_untranslated(item['name']) and 'reference_name' in item:
            item['name'] = item['reference_name']
        self.translations[lang] = self.DATA_CLASS(item)

    def translate(self):
        for lang in translations.LOCALE_MAPPING.keys():
            self.translate_one_language(lang)

    @staticmethod
    def is_untranslated(param):
        if not param:
            return True
        return param[0] + param[-1] == '[]'

    def __getattr__(self, item):
        return self.data[item]

    def __getitem__(self, item):
        return self.translations[item]

    @classmethod
    def deep_translate(cls, data: dict, lang):
        for key, item in data.items():
            new_key = _(key, lang)
            data[new_key] = item
            if key != new_key:
                del data[key]
            if isinstance(item, str) and cls.is_untranslated(item):
                data[new_key] = _(item, lang)
            if isinstance(item, dict):
                cls.deep_translate(data[new_key], lang)

    def set_release_date(self, release_date):
        self.data['release_date'] = release_date
        for lang in translations.LOCALE_MAPPING.keys():
            self.translations[lang].set_release_date(release_date)

    def matches(self, search_term, lang):
        compacted_search = extract_search_tag(search_term)
        item = self.translations[lang]
        if item.name == '`?`':
            return False
        lookups = {
            k: extract_search_tag(dig(item, k)) for k in self.LOOKUP_KEYS
        }
        for key, lookup in lookups.items():
            if compacted_search in lookup:
                return True
        return False

    def matches_precisely(self, search_term, lang):
        return extract_search_tag(self.translations[lang].name) == extract_search_tag(search_term)
