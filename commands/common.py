"""Shared imports, storage, and general helpers for the command modules."""

import asyncio
import math
import re
import shelve
import string
import traceback
from typing import Counter
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
import random
from custom_types import Neighbor, Item
from responses import ResponseRequest, ResponsePackage
from id_bundle import FF
from phoenix_bundle import PHOENIX
import difflib
import discord
import json
import datetime
import time
from PIL import Image
import requests
import os
import wordle_helper
import re, datetime


VERSION = "3.x";


swear_words = [];


unicodes = {
    0 : "\U00000030\U0000FE0F\U000020E3",
    1 : "\U00000031\U0000FE0F\U000020E3",
    2 : "\U00000032\U0000FE0F\U000020E3",
    3 : "\U00000033\U0000FE0F\U000020E3",
    4 : "\U00000034\U0000FE0F\U000020E3",
    5 : "\U00000035\U0000FE0F\U000020E3",
    6 : "\U00000036\U0000FE0F\U000020E3",
    7 : "\U00000037\U0000FE0F\U000020E3",
    8 : "\U00000038\U0000FE0F\U000020E3",
    9 : "\U00000039\U0000FE0F\U000020E3",
    "boost" : "\U0001F4B0",
    "perk" : "\U0001F5FF",
    "tag" : "\U0001F996",
    "icon" : "\U0001F48E",
    "mail" : "\U00002709",
    "rice" : "\U0001F33E",
    "rainbow" : "\U0001F308",
    "bee" : "\U0001F41D",
    "mushroom" : "\U0001F344",
    "selfie" : "\U0001F933",
    "crown" : "\U0001F451",
    "fox" : "\U0001F98A",
    "snowflake" : "\U00002744",
    "fries" : "\U0001F35F",
    "red_heart" : "\U00002764",
    "blueberry" : "\U0001FAD0",
    "strawberry" : "\U0001F353",
    "coffee" : "\U00002615",
    "t_rex" : "\U0001F996",
    "chicken" : "\U0001F414",
    "coin" : "\U0001FA99",
    "diamond" : "\U0001F48E",
    "crayon" : "\U0001F58D",
    "robot" : "\U0001F916",
    "nails" : "\U0001F485",
    "bank" : "\U0001F3E6",
    "check" : "\U00002705",
    "bot" : "\U0001F916",
    "ant" : "\U0001FAB3",
    "ghost" : "\U0001F47B",
    "back" : "\U000023CF",
    "butterfly" : "\U0001F98B",
    "cheetah" : "\U0001F406",
    "fox" : "\U0001F98A",
    "horse" : "\U0001F40E",
    "puppy" : "\U0001F436",
    "cabinet" : "\U0001F5C4",
    "trophy" : "\U0001F3C6",
    "first" : "\U0001F947",
    "second" : "\U0001F948",
    "third" : "\U0001F949",
    "clover" : "\U00001F34",
    "locked" : "🔒",
    "unlocked" : "🔓",
    "letters" : "\U0001F520",
    "gift" : "\U0001F381",
    "fire" : "\U0001F525",
    "star" : "\U00002B50",
    "anger" : "\U0001F620",
    "bee" : "\U0001F41D",
    "frog" : "\U0001F438",
    "goat" : "\U0001F410",
    "kitten" : "\U0001F408",
    "peacock" : "\U0001F99A",
}


swear_words = [];

test_list = ["some value"];


# If value given, stores to DB. If value None, retrieves data.
def remember(key, value=Ellipsis, delete=False):
    """Persistent key/value storage.
    
    Args:
        key: name of data
        value: value to store or Ellipsis to return data or None to delete data
        delete: delete data from storage if True
        
    """
    with shelve.open("data/persistentdata") as db:
        if value is not None and value is not Ellipsis:
            db[key] = value
            return value;
        elif value is None or delete:
            return db.pop(key, None)
        else:
            return db.get(key)

        
# p/q probability of returning True
def chance(q, p = 1):
    """
    p/q chance of returing True
    """
    possibilities = [0] * (q - p) + [1] * p
    return random.choice(possibilities);



def parse_mention(content):
    start = content.find("<@")
    end = content.find(">", start)
    if start == -1 or end == -1:
        raise ValueError("Not an ID")
    id_str = content[start+2:end]
    if id_str.startswith("!"):
        id_str = id_str[1:]
    if not id_str.isdigit():
        raise ValueError("Not an ID")
    return int(id_str)


def best_string_match(target, candidates):
    def similarity(x):
        return difflib.SequenceMatcher(None, x, target, autojunk=False).ratio()

    target_lower = target.lower()
    word_matches = [c for c in candidates if target_lower in c.lower().split()]
    substring_matches = [c for c in candidates if target_lower in c.lower()]

    if word_matches:
        best_match = max(word_matches, key=similarity)
    elif substring_matches:
        best_match = max(substring_matches, key=similarity)
    else:
        best_match = max(candidates, key=similarity)
        
    return best_match, similarity(best_match);


def convert_mentions_to_text(context: Context, str):
    role_id = "";
    start_pos = 0;
    end_pos = 0;
    for letter, i in enumerate(str):
        if letter == "<" and str[i + 1] == "@":
            start_pos = i;
            for ii in range(i + 2, len(str), 1):
                if not str[ii] == ">":
                    role_id += str[ii];
                else:
                    end_pos == ii;
                    break;
            break;
    try:
        role = context.guild.get_role(int(role_id));
        name = role.name;
        str = str[0:i] + "@" + name + str[ii + 1:];
        return str;
    except:
        pass;


def get_code_replacement(str = None, all = None):
    if is_within_dates((11,9),(12,31)):
        codes = {
            "&FFP_LOGO": "<:farmmas_ffp_logo:1170071905089368075>",
            "&FF_LOGO": "<:farmmas_ff_logo:1170071779037945907>",
            "&FFJ_LOGO": "<:farmmas_ffj_logo:1170071826517467136>",
            "&FFG_LOGO": "<:farmmas_ffg_logo:1173333335876050985>",
            "&FFR_LOGO": "<:farmmas_ffr_logo:1170071889029386404>",
            "&FFC_LOGO": "<:farmmas_ffc_logo:1454605765330341999>",
            "&FFP_TAG": "#L92LUVQJ",
            "&FF_TAG": "#9UPRVCUR",
            "&FFJ_TAG": "#PC8VCJ8Q",
            "&FFG_TAG": "#QP8JURUC",
            "&FFJ2_TAG": "#RGP8J9GP",
            "&FFR_TAG": "#L92LUVQJ",
        }
    else:
        codes = {
            "&FFP_LOGO": "<:ffp_logo:1111011980061462538>",
            "&FF_LOGO": "<:ff_logo:1111011971953872976>",
            "&FFJ_LOGO": "<:ffj_logo:1111011976320122880>",
            "&FFJ2_LOGO": "<:ffj2_logo:1335746631236194344>",
            "&FFG_LOGO": "<:ffg_logo:1173332572642754560>",
            "&FFC_LOGO": "<:ffc_logo:1342333117607710741>",
            "&FFR_LOGO": "<:ffr_logo:1111011982787743866>",
            "&FFP_TAG": "#L92LUVQJ",
            "&FF_TAG": "#9UPRVCUR",
            "&FFJ_TAG": "#PC8VCJ8Q",
            "&FFG_TAG": "#QP8JURUC",
            "&FFJ2_TAG": "#RGP8J9GP",
            "&FFC_TAG": "#G8P8YGPG",
            "&FFR_TAG": "#L92LUVQJ",
        }
    if all:
        return codes;
    return codes[str];


#Written with assistance from chatGPT
def is_within_dates(start_date, end_date=None):
    current_date = datetime.datetime.now().date()
    start_date = datetime.datetime(current_date.year, *start_date).date() if len(start_date) == 2 else datetime.datetime(*start_date).date()
    if end_date:
        end_date = datetime.datetime(current_date.year, *end_date).date() if len(end_date) == 2 else datetime.datetime(*end_date).date();
    if end_date:
        return start_date <= current_date <= end_date
    else:
        return current_date >= start_date

