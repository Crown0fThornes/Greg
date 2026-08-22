from math import floor
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands.commands as commands
import time
import random
import sqlite3
import json
import password_manager
import math
import discord
import difflib
from pathlib import Path
import datetime
import wordle_helper

LOCAL_UTC_OFFSET = -4  # EDT
LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=LOCAL_UTC_OFFSET))

red_wordle_emojis = {
    0: "<:0_a:1117155743754354829>",
    1: "<:0_b:1117155746182869162>",
    2: "<:0_c:1117155748372299877>",
    3: "<:0_d:1117155751329284166>",
    4: "<:0_e:1117155753338359808>",
    5: "<:0_f:1117155755653603339>",
    6: "<:0_g:1117155757931114697>",
    7: "<:0_h:1117155759847899176>",
    8: "<:0_i:1117155761794060389>",
    9: "<:0_j:1117155764054798526>",
    10: "<:0_k:1117155766659465276>",
    11: "<:0_l:1117155768827924651>",
    12: "<:0_m:1117155771440963654>",
    13: "<:0_n:1117155773454233692>",
    14: "<:0_o:1117155775568158845>",
    15: "<:0_p:1117156672889172009>",
    16: "<:0_q:1117156676131377243>",
    17: "<:0_r:1117156678241095731>",
    18: "<:0_s:1117156680904486942>",
    19: "<:0_t:1117156683228139630>",
    20: "<:0_u:1117156685866352813>",
    21: "<:0_v:1117156687774765097>",
    22: "<:0_w:1117156690333274162>",
    23: "<:0_x:1117156692312993833>",
    24: "<:0_y:1117156694837952603>",
    25: "<:0_z:1117156697258086431>"
}
yellow_wordle_emojis = {
    0: "<:1_a:1117151655343955988>",
    1: "<:1_b:1117151657940226138>",
    2: "<:1_c:1117151659534057593>",
    3: "<:1_d:1117151662902083694>",
    4: "<:1_e:1117151664701444216>",
    5: "<:1_f:1117151667037679677>",
    6: "<:1_g:1117151668715389038>",
    7: "<:1_h:1117151670644781086>",
    8: "<:1_i:1117151673173946468>",
    9: "<:1_j:1117151675141079110>",
    10: "<:1_k:1117151677288562688>",
    11: "<:1_l:1117151684423077998>",
    12: "<:1_m:1117151686251786341>",
    13: "<:1_n:1117151687820451880>",
    14: "<:1_o:1117151690014081066>",
    15: "<:1_p:1117151692165750834>",
    16: "<:1_q:1117151694585872527>",
    17: "<:1_r:1117155116135497808>",
    18: "<:1_s:1117151697576411359>",
    19: "<:1_t:1117155118484303872>",
    20: "<:1_u:1117151701112213504>",
    21: "<:1_v:1117155120422068234>",
    22: "<:1_w:1117151704656396338>",
    23: "<:1_x:1117155122238210148>",
    24: "<:1_y:1117151709270118460>",
    25: "<:1_z:1117151711522459649>"
}
green_wordle_emojis = {
    0: "<:2_a:1117132571369816185>",
    1: "<:2_b:1117132573949296762>",
    2: "<:2_c:1117132575677354014>",
    3: "<:2_d:1117132577736765510>",
    4: "<:2_e:1117132584665755779>",
    5: "<:2_f:1117132588964909187>",
    6: "<:2_g:1117132591380836412>",
    7: "<:2_h:1117132601417801840>",
    8: "<:2_i:1117132604202811442>",
    9: "<:2_j:1117132605838602260>",
    10: "<:2_k:1117132609030471761>",
    11: "<:2_l:1117132611228278805>",
    12: "<:2_m:1117132614533398538>",
    13: "<:2_n:1117132616810909786>",
    14: "<:2_o:1117132619121950741>",
    15: "<:2_p:1117133811432570940>",
    16: "<:2_q:1117133815580725441>",
    17: "<:2_r:1117133818487382066>",
    18: "<:2_s:1117133820769095830>",
    19: "<:2_t:1117133824262934628>",
    20: "<:2_u:1117133829031874721>",
    21: "<:2_v:1117133831405850714>",
    22: "<:2_w:1117133833796587671>",
    23: "<:2_x:1117133836355109004>",
    24: "<:2_y:1117133838162874470>",
    25: "<:2_z:1117133841119846410>"
}
purple_wordle_emojis = {
    0: "<:3_a:1129837059624947723>",
    1: "<:3_b:1129837062107963483>",
    2: "<:3_c:1129837064129609940>",
    3: "<:3_d:1129837066319056969>",
    4: "<:3_e:1129837069057921116>",
    5: "<:3_f:1129837071012479076>",
    6: "<:3_g:1129837072904093928>",
    7: "<:3_h:1129837079011004416>",
    8: "<:3_i:1129837081535987853>",
    9: "<:3_j:1129837084128071790>",
    10: "<:3_k:1129837086996971571>",
    11: "<:3_l:1129837088896979015>",
    12: "<:3_m:1129837090977353799>",
    13: "<:3_n:1129837092529254541>",
    14: "<:3_o:1129837095112945694>",
    15: "<:3_p:1129837097470132254>",
    16: "<:3_q:1129837099550527570>",
    17: "<:3_r:1129837504527339670>",
    18: "<:3_s:1129837102486528101>",
    19: "<:3_t:1129837507337531422>",
    20: "<:3_u:1129837509027827712>",
    21: "<:3_v:1129837106051682365>",
    22: "<:3_w:1129837658122752131>",
    23: "<:3_x:1129837109335838770>",
    24: "<:3_y:1129837510667800697>",
    25: "<:3_z:1129837113005842432>",
}

async def wordle_easy(activator: Neighbor, context: Context, response: ResponsePackage = None):
    
    with open("words.txt", "r") as fWords:
        words = [line.strip() for line in fWords.readlines()]
    with open("answers.txt", "r") as fAnswers:
        answers = [line.strip() for line in fAnswers.readlines()]
    answers = answers[0:1499]

    if response is None:
        daily_limit_hit = False;
    
        # ── DAILY WORDLE XP RESET & CHECK ──────────────────────────────────────────────
        daily_limit = Neighbor.get_XP_for_level(3)
        today_str   = datetime.date.today().isoformat()
        cap_item = activator.get_item_of_name("Wordle Daily XP")
        if cap_item:
            # if the stored date isn't today, reset
            if cap_item.get_value("date") != today_str:
                cap_item.update_value("date", today_str)
                cap_item.update_value("xp",   0)
                activator.update_item(cap_item)
            xp_today = int(cap_item.get_value("xp"))
        else:
            # first play today: create tracking item
            cap_item = Item("Wordle Daily XP", "xp_daily", -1,
                        date=today_str, xp=0, hidden="true")
            activator.bestow_item(cap_item)
            xp_today = 0

        # if they've already hit the cap, bail out
        if xp_today >= daily_limit:
            daily_limit_hit = True;
        # ───────────────────────────────────────────────────────────────────────────────
        
        res = "**Welcome to Greg's ";
        res += green_wordle_emojis[22] + yellow_wordle_emojis[14] + green_wordle_emojis[17] + green_wordle_emojis[3] + red_wordle_emojis[11] + green_wordle_emojis[4];
        res += "!**\n\nI have already selected a word! Guess valid 5-letter words in this channel and I will give clues toward the answer. If you write a message that is not a valid 5 letter word in my dictionary, I will just ignore it. You have two minutes to make each guess.\n\n**Scoring:** Tom will also play alongside you and I will reveal his guesses once you have successfully guessed the word. You will get XP based on how many guesses it takes you to get the word. If you get the word in fewer guesses than Tom, you will get double XP! Let's begin, guess your first word!\n\n**Note:** Different forms of words are fair game. For example, plural words may be chosen as the Wordle and may be guessed.";
        target = await context.send(res, reply = True);
        start_time = time.monotonic()
        response_context = Context(message = target)
        answer = random.choice(answers);
        # await context.send(answer);
        def key(context):
            if not context.content.lower() in words:
                return False;
            return True;
        
        ResponseRequest(wordle_easy, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = [], daily_limit_hit = daily_limit_hit, start_time=start_time)
        
    else:
        print("here! wordle")
        guess_list = response.values["guesses"];
        answer = response.values["answer"];
        dlh = response.values["daily_limit_hit"]
        start_time = response.values["start_time"]
        candidate = response.content.lower();
        guess_list.append(candidate);
        response = wordle_helper.get_response(answer, candidate);
        if len(guess_list) == 1:
            await context.send("Red: This letter is not in the word.\nYellow: This letter is in the word in a different position (careful, this is slightly different from NYT Wordle mechanics)\nGreen: This letter is in the word in this position\nPurple: Easy Mode Only, This letter is in the word in this position AND another position")
        if not "0" in response and not "1" in response:
            end_time = time.monotonic();
            # correct!
            res = "**You got it!!**\n\n";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);

            res = "**Let's see how Tom did!**\n\n";
            word_info = wordle_helper.WordInfo();
            tom_guesses = [];
            while not word_info.is_word_complete():
                possible = word_info.cleanse(words);
                if len(possible) == 0 or len(tom_guesses) > 15:
                    await context.send("Uh oh! Something has gone wrong on my end.");
                    return
                sorted = wordle_helper.sort_by_letter_frequency(possible);
                difficulty = int(len(possible) / 2);
                if difficulty == 0:
                    difficulty += 1;
                if len(sorted) > difficulty:
                    next_guess = random.choice(sorted[:difficulty]);
                else:
                    next_guess = random.choice(sorted);
                tom_guesses.append(next_guess);
                response = wordle_helper.get_response(answer, next_guess);
                word_info.register_guess(next_guess, response)
                for i, char in enumerate(next_guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            await context.send(res);
            num_guesses = len(guess_list);
            num_tom_guesses = len(tom_guesses);
            try:
                if num_guesses < 9:
                    xp = 25 * (9 - len(guess_list));
                    if len(guess_list) < len(tom_guesses):
                        await context.send(f"Wow! You beat tom by {len(tom_guesses) - len(guess_list)} guesses!\n\nYou get {xp}xp for getting the word in {len(guess_list)}, doubled for beating Tom! {xp * 2}xp total!");
                        xp *= 2;
                    else:
                        await context.send(f"Unfortunately you did not beat tom!!\n\nHowever, you get {xp}xp for getting the word in {len(guess_list)}!");
                    if dlh:
                        await context.send("You've actually hit the daily limit for earning XP with Wordle, so no XP for this round. However, you can continue to play for fun!")
                    else:
                        await inc_xp(activator, xp, context)
                        cap_item.update_value("xp", int(cap_item.get_value("xp")) + xp)
                        activator.update_item(cap_item)
                else:
                    await context.send(f"Unfortunately, {len(guess_list)} guesses is too many to earn XP! Good job getting the Wordle though, better luck next time!");
                    
            except:
                pass
            import requests

            def get_definition(word):
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                res = requests.get(url).json()
                canonical_word = res[0]["word"]
                return canonical_word, res[0]["meanings"][0]["definitions"][0]["definition"]

            definiton = get_definition(answer)
            await context.send(f"**Definition**\n{definiton[0]}: {definiton[1]}")
            
            await update_wordle_leaderboard(activator, end_time-start_time, len(guess_list));
        else:
            res = "";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "3":
                        res += purple_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);
            response_context = Context(message = target);
            def key(context):
                if not context.content.lower() in words:
                    return False;
                return True;
            ResponseRequest(wordle_easy, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = guess_list, daily_limit_hit=dlh, start_time=start_time)


async def wordle_hard(activator: Neighbor, context: Context, response: ResponsePackage = None):
        
    daily_limit_hit = False;
    
    # ── DAILY WORDLE XP RESET & CHECK ──────────────────────────────────────────────
    daily_limit = Neighbor.get_XP_for_level(6)
    today_str   = datetime.date.today().isoformat()
    cap_item = activator.get_item_of_name("Wordle Daily XP")
    if cap_item:
        # if the stored date isn't today, reset
        if cap_item.get_value("date") != today_str:
            cap_item.update_value("date", today_str)
            cap_item.update_value("xp",   0)
            activator.update_item(cap_item)
        xp_today = int(cap_item.get_value("xp"))
    else:
        # first play today: create tracking item
        cap_item = Item("Wordle Daily XP", "xp_daily", -1,
                    date=today_str, xp=0, hidden="true")
        activator.bestow_item(cap_item)
        xp_today = 0

    # if they've already hit the cap, bail out
    if xp_today >= daily_limit:
        daily_limit_hit = True;
    # ───────────────────────────────────────────────────────────────────────────────
    
    with open("words.txt", "r") as fWords:
        words = [line.strip() for line in fWords.readlines()]
    with open("answers.txt", "r") as fAnswers:
        answers = [line.strip() for line in fAnswers.readlines()]
    answers = answers[0:3499]

    if response is None:
        res = "**Welcome to Greg's ";
        res += green_wordle_emojis[22] + yellow_wordle_emojis[14] + green_wordle_emojis[17] + green_wordle_emojis[3] + red_wordle_emojis[11] + green_wordle_emojis[4];
        res += " HARD MODE!**\n\nYou know the drill! Hard mode wordle works the same as regular mode with a few changes. Firstly, there are 1500 more possible Wordles. Secondly, you play against Rose instead of Tom, who is better at guessing. Thirdly, more XP is available to be won but you must get the word in 6 guesses or less instead of 8 to earn any. Finally, no purple letters will be shown.\n\n**Scoring:** Rose will also play alongside you and I will reveal her guesses once you have successfully guessed the word. You will get XP based on how many guesses it takes you to get the word. If you get the word in fewer guesses than Rose, you will get double XP! Let's begin, guess your first word!\n\n**Note:** Different forms of words are fair game. For example, plural words may be chosen as the Wordle and may be guessed.";
        target = await context.send(res, reply = True);
        start_time = time.monotonic()
        response_context = Context(message = target)
        answer = random.choice(answers);
        # answer = "dived"
        # await context.send(answer);
        def key(context):
            if not context.content.lower() in words:
                return False;
            return True;
        ResponseRequest(wordle_hard, "guess", "MESSAGE", context, response_context, answer = answer, key = key, guesses = [], daily_limit_hit=daily_limit_hit, start_time=start_time)
    else:
        guess_list = response.values["guesses"];
        answer = response.values["answer"];
        dlh = response.values["daily_limit_hit"]
        start_time = response.values["start_time"]
        candidate = response.content.lower();
        guess_list.append(candidate);
        response = wordle_helper.get_response(answer, candidate);
        if len(guess_list) == 1:
            await context.send("Red: This letter is not in the word.\nYellow: This letter is in the word in a different position (careful, this is slightly different from NYT Wordle mechanics)\nGreen: This letter is in the word in this position\n~~Purple: Easy Mode Only, This letter is in the word in this position AND another position~~")
        if not "0" in response and not "1" in response:
            # correct!
            end_time = time.monotonic()
            res = "**You got it!!**\n\n";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);

            res = "**Let's see how Rose did!**\n\n";
            word_info = wordle_helper.WordInfo();
            tom_guesses = [];
            choices = [i + 1 for i in range(5)];
            difficulty = random.choice(choices)
            while not word_info.is_word_complete():
                possible = word_info.cleanse(words);
                if len(possible) == 0 or len(tom_guesses) > 15:
                    await context.send("Uh oh! Something has gone wrong on my end.");
                    return
                sorted = wordle_helper.sort_by_letter_frequency(possible);
                if len(sorted) > difficulty:
                    next_guess = random.choice(sorted[:difficulty]);
                else:
                    next_guess = random.choice(sorted);
                tom_guesses.append(next_guess);
                response = wordle_helper.get_response(answer, next_guess);
                word_info.register_guess(next_guess, response)
                for i, char in enumerate(next_guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            await context.send(res);
            num_guesses = len(guess_list);
            num_tom_guesses = len(tom_guesses);
            try:
                if num_guesses < 7:
                    xp = 85 * (7 - len(guess_list));
                    if len(guess_list) < len(tom_guesses):
                        await context.send(f"Wow! You beat Rose by {len(tom_guesses) - len(guess_list)} guesses!\n\nYou get {xp}xp for getting the word in {len(guess_list)}, doubled for beating Rose! {xp * 2}xp total!");
                        xp *= 2;
                    else:
                        await context.send(f"Unfortunately you did not beat Rose!!\n\nHowever, you get {xp}xp for getting the word in {len(guess_list)}!");
                    if dlh:
                        await context.send("You've actually hit the daily limit for earning XP with Wordle, so no XP for this round. However, you can continue to play for fun!")
                    else:
                        await inc_xp(activator, xp, context)
                        cap_item.update_value("xp", int(cap_item.get_value("xp")) + xp)
                        activator.update_item(cap_item)
                else:
                    await context.send(f"Unfortunately, {len(guess_list)} guesses is too many to earn XP! Good job getting the Wordle though, better luck next time!");
            except:
                pass
            import requests

            def get_definition(word):
                url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                res = requests.get(url).json()
                canonical_word = res[0]["word"]
                return canonical_word, res[0]["meanings"][0]["definitions"][0]["definition"]

            definiton = get_definition(answer)
            await context.send(f"**Definition**\n{definiton[0]}: {definiton[1]}")
            
            await update_wordle_leaderboard(activator, end_time-start_time, len(guess_list))
            
        else:
            res = "";
            for guess in guess_list[-9:]:
                response = wordle_helper.get_response(answer, guess);
                for i, char in enumerate(guess):
                    if response[i] == "0":
                        res += red_wordle_emojis[ord(char) - 97];
                    elif response[i] == "1":
                        res += yellow_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2":
                        res += green_wordle_emojis[ord(char) - 97];
                    elif response[i] == "2" or response[i] == "3":
                        res += green_wordle_emojis[ord(char) - 97];
                res += "\n";
            target = await context.send(res);
            response_context = Context(message = target);
            def key(context):
                if not context.content.lower() in words:
                    return False;
                return True;
            ResponseRequest(wordle_hard, "guess", "MESSAGE", context, response_context, key = key, answer = answer, guesses = guess_list, daily_limit_hit=dlh, start_time=start_time)

@command_handler.Command(AccessType.PRIVATE, desc = "Play Wordle!", generic=True)
async def wordle(activator: Neighbor, context: Context):
    if not activator.get_item_of_name("Greg Wordle Minigame") and not activator.get_item_of_name("Wordle 2 (Hard Mode)") and not activator.ID == 355169964027805698:
        await context.send("Whoops! Looks like you haven't purchased the Wordle minigame from my rss yet!\n\nPlay with someone else or buy it for yourself by calling $rss. #sorrynotsorry");
        return;
    if activator.get_item_of_name("Wordle 2 (Hard Mode)"):
        await wordle_hard(activator, context);
        return;
    else:
        await wordle_easy(activator, context);
        return;
    
async def update_wordle_leaderboard(activator: Neighbor, seconds_to_solve, num_guesses):
    