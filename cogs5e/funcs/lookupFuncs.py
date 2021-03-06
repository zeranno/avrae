"""
Created on Jan 13, 2017

@author: andrew
"""
import itertools
import json
import logging

from cogs5e.models.background import Background
from cogs5e.models.errors import NoActiveBrew
from cogs5e.models.homebrew.bestiary import Bestiary
from cogs5e.models.homebrew.tome import Tome
from cogs5e.models.monster import Monster
from cogs5e.models.race import Race
from cogs5e.models.spell import Spell
from utils.functions import parse_data_entry, search_and_select, search

HOMEBREW_EMOJI = "<:homebrew:434140566834511872>"
HOMEBREW_ICON = "https://avrae.io/assets/img/homebrew.png"

log = logging.getLogger(__name__)


class Compendium:
    def __init__(self):
        with open('./res/conditions.json', 'r') as f:
            self.conditions = json.load(f)
        with open('./res/rules.json', 'r') as f:
            self.rules = json.load(f)
        with open('./res/feats.json', 'r') as f:
            self.feats = json.load(f)
        with open('./res/races.json', 'r') as f:
            _raw = json.load(f)
            self.rfeats = []
            self.fancyraces = [Race.from_data(r) for r in _raw]
            for race in _raw:
                for entry in race['entries']:
                    if isinstance(entry, dict) and 'name' in entry:
                        temp = {'name': "{}: {}".format(race['name'], entry['name']),
                                'text': parse_data_entry(entry['entries']), 'srd': race['srd']}
                        self.rfeats.append(temp)
        with open('./res/classes.json', 'r') as f:
            self.classes = json.load(f)
        with open('./res/classfeats.json') as f:
            self.cfeats = json.load(f)
        with open('./res/bestiary.json', 'r') as f:
            self.monsters = json.load(f)
            self.monster_mash = [Monster.from_data(m) for m in self.monsters]
        with open('./res/spells.json', 'r') as f:
            self.spells = [Spell.from_data(r) for r in json.load(f)]
        with open('./res/items.json', 'r') as f:
            _items = json.load(f)
            self.items = [i for i in _items if i.get('type') is not '$']
        with open('./res/backgrounds.json', 'r') as f:
            self.backgrounds = [Background.from_data(b) for b in json.load(f)]
        self.subclasses = self.load_subclasses()
        with open('./res/itemprops.json', 'r') as f:
            self.itemprops = json.load(f)
        with open('./res/names.json', 'r') as f:
            self.names = json.load(f)

    def load_subclasses(self):
        s = []
        for _class in self.classes:
            subclasses = _class.get('subclasses', [])
            for sc in subclasses:
                sc['name'] = f"{_class['name']}: {sc['name']}"
            s.extend(subclasses)
        return s


c = Compendium()


# ----- Monster stuff
async def select_monster_full(ctx, name, cutoff=5, return_key=False, pm=False, message=None, list_filter=None,
                              srd=False, return_metadata=False):
    """
    Gets a Monster from the compendium and active bestiary/ies.
    """
    try:
        bestiary = await Bestiary.from_ctx(ctx)
        custom_monsters = bestiary.monsters
        bestiary_id = bestiary.id
    except NoActiveBrew:
        custom_monsters = []
        bestiary_id = None
    choices = list(itertools.chain(c.monster_mash, custom_monsters))
    if ctx.guild:
        async for servbestiary in ctx.bot.mdb.bestiaries.find({"server_active": str(ctx.guild.id)}, ['monsters']):
            choices.extend(
                Monster.from_bestiary(m) for m in servbestiary['monsters'] if servbestiary['_id'] != bestiary_id)

    if srd:
        if list_filter:
            old = list_filter
            list_filter = lambda e: old(e) and e.srd
        else:
            list_filter = lambda e: e.srd
        message = "Only results from the 5e SRD are included."

    def get_homebrew_formatted_name(monster):
        if monster.source == 'homebrew':
            return f"{monster.name} ({HOMEBREW_EMOJI})"
        return monster.name

    return await search_and_select(ctx, choices, name, lambda e: e.name, cutoff, return_key, pm, message, list_filter,
                                   selectkey=get_homebrew_formatted_name, return_metadata=return_metadata)


# ---- SPELL STUFF ----
async def select_spell_full(ctx, name, cutoff=5, return_key=False, pm=False, message=None, list_filter=None,
                            srd=False, search_func=None, return_metadata=False):
    """
    Gets a Spell from the compendium and active tome(s).
    """
    choices = await get_spell_choices(ctx)

    if srd:
        if list_filter:
            old = list_filter
            list_filter = lambda e: old(e) and e.srd
        else:
            list_filter = lambda e: e.srd
        message = "Only results from the 5e SRD are included."

    def get_homebrew_formatted_name(spell):
        if spell.source == 'homebrew':
            return f"{spell.name} ({HOMEBREW_EMOJI})"
        return spell.name

    return await search_and_select(ctx, choices, name, lambda e: e.name, cutoff, return_key, pm, message, list_filter,
                                   selectkey=get_homebrew_formatted_name, search_func=search_func,
                                   return_metadata=return_metadata)


async def get_spell_choices(ctx):
    try:
        tome = await Tome.from_ctx(ctx)
        custom_spells = tome.spells
        tome_id = tome.id
    except NoActiveBrew:
        custom_spells = []
        tome_id = None
    choices = list(itertools.chain(c.spells, custom_spells))
    if ctx.guild:
        async for servtome in ctx.bot.mdb.tomes.find({"server_active": str(ctx.guild.id)}, ['spells']):
            choices.extend(Spell.from_dict(s) for s in servtome['spells'] if servtome['_id'] != tome_id)
    return choices


async def get_castable_spell(ctx, name, choices=None):
    if choices is None:
        choices = await get_spell_choices(ctx)

    result = search(choices, name, lambda sp: sp.name)
    if result and result[1]:
        return result[0]
    return None
