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


# Wordle logic written entirely by Lincoln, but ChatGPT consolidated Hard Mode & Easy mode into one branch. It also cleaned up the code which, while in a style I wouldn't go for, is hard to be mad about.
async def wordle_easy(
    activator: Neighbor,
    context: Context,
    response: ResponsePackage = None
):
    await wordle_game(
        activator,
        context,
        response,
        hard_mode=False
    )


async def wordle_hard(
    activator: Neighbor,
    context: Context,
    response: ResponsePackage = None
):
    await wordle_game(
        activator,
        context,
        response,
        hard_mode=True
    )


async def wordle_game(
    activator: Neighbor,
    context: Context,
    response: ResponsePackage = None,
    hard_mode: bool = False
):
    # ── MODE SETTINGS ────────────────────────────────────────────────────────

    if hard_mode:
        callback = wordle_hard
        opponent_name = "Rose"
        answer_count = 3500
        daily_limit_level = 6
        max_xp_guesses = 6
        xp_multiplier = 85
    else:
        callback = wordle_easy
        opponent_name = "Tom"
        answer_count = 1500
        daily_limit_level = 3
        max_xp_guesses = 8
        xp_multiplier = 25

    # ── WORD LISTS ───────────────────────────────────────────────────────────

    with open("words.txt", "r") as f:
        words = [line.strip() for line in f]

    with open("answers.txt", "r") as f:
        answers = [line.strip() for line in f][:answer_count]

    # ── NEW GAME ─────────────────────────────────────────────────────────────

    if response is None:
        daily_limit = Neighbor.get_XP_for_level(daily_limit_level)
        today_str = datetime.date.today().isoformat()

        cap_item = activator.get_item_of_name("Wordle Daily XP")

        if cap_item:
            if cap_item.get_value("date") != today_str:
                cap_item.update_value("date", today_str)
                cap_item.update_value("xp", 0)
                activator.update_item(cap_item)

            xp_today = int(cap_item.get_value("xp"))

        else:
            cap_item = Item(
                "Wordle Daily XP",
                "xp_daily",
                -1,
                date=today_str,
                xp=0,
                hidden="true"
            )
            activator.bestow_item(cap_item)
            xp_today = 0

        daily_limit_hit = xp_today >= daily_limit

        wordle_title = (
            green_wordle_emojis[22]
            + yellow_wordle_emojis[14]
            + green_wordle_emojis[17]
            + green_wordle_emojis[3]
            + red_wordle_emojis[11]
            + green_wordle_emojis[4]
        )

        if hard_mode:
            res = (
                f"**Welcome to Greg's {wordle_title} HARD MODE!**\n\n"
                "You know the drill! Hard mode wordle works the same as regular "
                "mode with a few changes. Firstly, there are 1500 more possible "
                "Wordles. Secondly, you play against Rose instead of Tom, who is "
                "better at guessing. Thirdly, more XP is available to be won but "
                "you must get the word in 6 guesses or less instead of 8 to earn "
                "any. Finally, no purple letters will be shown.\n\n"
                "**Scoring:** Rose will also play alongside you and I will reveal "
                "her guesses once you have successfully guessed the word. You will "
                "get XP based on how many guesses it takes you to get the word. "
                "If you get the word in fewer guesses than Rose, you will get "
                "double XP! Let's begin, guess your first word!\n\n"
                "**Note:** Different forms of words are fair game. For example, "
                "plural words may be chosen as the Wordle and may be guessed."
            )
        else:
            res = (
                f"**Welcome to Greg's {wordle_title}!**\n\n"
                "I have already selected a word! Guess valid 5-letter words in "
                "this channel and I will give clues toward the answer. If you "
                "write a message that is not a valid 5 letter word in my "
                "dictionary, I will just ignore it. You have two minutes to make "
                "each guess.\n\n"
                "**Scoring:** Tom will also play alongside you and I will reveal "
                "his guesses once you have successfully guessed the word. You "
                "will get XP based on how many guesses it takes you to get the "
                "word. If you get the word in fewer guesses than Tom, you will "
                "get double XP! Let's begin, guess your first word!\n\n"
                "**Note:** Different forms of words are fair game. For example, "
                "plural words may be chosen as the Wordle and may be guessed."
            )

        target = await context.send(res, reply=True)

        start_time = time.monotonic()
        response_context = Context(message=target)
        answer = random.choice(answers)

        def key(context):
            return context.content.lower() in words

        ResponseRequest(
            callback,
            "guess",
            "MESSAGE",
            context,
            response_context,
            answer=answer,
            key=key,
            guesses=[],
            daily_limit_hit=daily_limit_hit,
            start_time=start_time
        )

        return

    # ── EXISTING GAME ────────────────────────────────────────────────────────

    guess_list = response.values["guesses"]
    answer = response.values["answer"]
    daily_limit_hit = response.values["daily_limit_hit"]
    start_time = response.values["start_time"]

    candidate = response.content.lower()
    guess_list.append(candidate)

    clue_response = wordle_helper.get_response(answer, candidate)

    if len(guess_list) == 1:
        purple_description = (
            "~~Purple: Easy Mode Only, This letter is in the word in this "
            "position AND another position~~"
            if hard_mode
            else
            "Purple: Easy Mode Only, This letter is in the word in this "
            "position AND another position"
        )

        await context.send(
            "Red: This letter is not in the word.\n"
            "Yellow: This letter is in the word in a different position "
            "(careful, this is slightly different from NYT Wordle mechanics)\n"
            "Green: This letter is in the word in this position\n"
            f"{purple_description}"
        )

    # ── HELPER FOR RENDERING GUESSES ─────────────────────────────────────────

    def render_guess(guess):
        clue = wordle_helper.get_response(answer, guess)
        result = ""

        for i, char in enumerate(guess):
            if clue[i] == "0":
                result += red_wordle_emojis[ord(char) - 97]

            elif clue[i] == "1":
                result += yellow_wordle_emojis[ord(char) - 97]

            elif clue[i] == "2":
                result += green_wordle_emojis[ord(char) - 97]

            elif clue[i] == "3":
                if hard_mode:
                    result += green_wordle_emojis[ord(char) - 97]
                else:
                    result += purple_wordle_emojis[ord(char) - 97]

        return result

    # ── CORRECT ANSWER ───────────────────────────────────────────────────────

    if "0" not in clue_response and "1" not in clue_response:
        end_time = time.monotonic()

        res = "**You got it!!**\n\n"

        for guess in guess_list[-9:]:
            res += render_guess(guess) + "\n"

        await context.send(res)

        # ── OPPONENT ─────────────────────────────────────────────────────────

        res = f"**Let's see how {opponent_name} did!**\n\n"

        word_info = wordle_helper.WordInfo()
        opponent_guesses = []

        if hard_mode:
            difficulty = random.randint(1, 5)

        while not word_info.is_word_complete():
            possible = word_info.cleanse(words)

            if len(possible) == 0 or len(opponent_guesses) > 15:
                await context.send("Uh oh! Something has gone wrong on my end.")
                return

            sorted_words = wordle_helper.sort_by_letter_frequency(possible)

            if hard_mode:
                opponent_pool_size = difficulty
            else:
                opponent_pool_size = max(1, len(possible) // 2)

            if len(sorted_words) > opponent_pool_size:
                next_guess = random.choice(
                    sorted_words[:opponent_pool_size]
                )
            else:
                next_guess = random.choice(sorted_words)

            opponent_guesses.append(next_guess)

            opponent_response = wordle_helper.get_response(
                answer,
                next_guess
            )

            word_info.register_guess(
                next_guess,
                opponent_response
            )

            res += render_guess(next_guess) + "\n"

        await context.send(res)

        # ── XP ────────────────────────────────────────────────────────────────

        num_guesses = len(guess_list)
        num_opponent_guesses = len(opponent_guesses)

        try:
            if num_guesses <= max_xp_guesses:
                xp = xp_multiplier * (
                    max_xp_guesses + 1 - num_guesses
                )

                if num_guesses < num_opponent_guesses:
                    difference = num_opponent_guesses - num_guesses

                    await context.send(
                        f"Wow! You beat {opponent_name} by "
                        f"{difference} guesses!\n\n"
                        f"You get {xp}xp for getting the word in "
                        f"{num_guesses}, doubled for beating "
                        f"{opponent_name}! {xp * 2}xp total!"
                    )

                    xp *= 2

                else:
                    await context.send(
                        f"Unfortunately you did not beat "
                        f"{opponent_name}!!\n\n"
                        f"However, you get {xp}xp for getting the "
                        f"word in {num_guesses}!"
                    )

                if daily_limit_hit:
                    await context.send(
                        "You've actually hit the daily limit for earning XP "
                        "with Wordle, so no XP for this round. However, you "
                        "can continue to play for fun!"
                    )

                else:
                    await commands.inc_xp(activator, xp, context)

                    cap_item = activator.get_item_of_name(
                        "Wordle Daily XP"
                    )

                    cap_item.update_value(
                        "xp",
                        int(cap_item.get_value("xp")) + xp
                    )

                    activator.update_item(cap_item)

            else:
                await context.send(
                    f"Unfortunately, {num_guesses} guesses is too many "
                    f"to earn XP! Good job getting the Wordle though, "
                    f"better luck next time!"
                )

        except Exception:
            pass

        # ── DEFINITION ────────────────────────────────────────────────────────

        import requests

        def get_definition(word):
            url = (
                "https://api.dictionaryapi.dev/api/v2/entries/en/"
                f"{word}"
            )
            res = requests.get(url).json()

            canonical_word = res[0]["word"]
            definition = (
                res[0]["meanings"][0]["definitions"][0]["definition"]
            )

            return canonical_word, definition

        try:
            definition = get_definition(answer)

            await context.send(
                f"**Definition**\n"
                f"{definition[0]}: {definition[1]}"
            )
        except:
            pass
        
        # ── LEADERBOARD ──────────────────────────────────────────────────────

        await update_wordle_leaderboard(
            activator,
            context,
            end_time - start_time,
            num_guesses
        )

        return

    # ── INCORRECT GUESS ──────────────────────────────────────────────────────

    res = ""

    for guess in guess_list[-9:]:
        res += render_guess(guess) + "\n"

    target = await context.send(res)
    response_context = Context(message=target)

    def key(context):
        return context.content.lower() in words

    ResponseRequest(
        callback,
        "guess",
        "MESSAGE",
        context,
        response_context,
        key=key,
        answer=answer,
        guesses=guess_list,
        daily_limit_hit=daily_limit_hit,
        start_time=start_time
    )


@command_handler.Command(
    AccessType.PRIVATE,
    desc="Play Wordle!",
    generic=True
)
async def wordle(activator: Neighbor, context: Context):
    has_easy = activator.get_item_of_name("Greg Wordle Minigame")
    has_hard = activator.get_item_of_name("Wordle 2 (Hard Mode)")
    is_owner = activator.ID == 355169964027805698

    if not has_easy and not has_hard and not is_owner:
        await context.send(
            "Whoops! Looks like you haven't purchased the Wordle minigame "
            "from my rss yet!\n\n"
            "Play with someone else or buy it for yourself by calling $rss. "
            "#sorrynotsorry"
        )
        return

    if has_hard:
        await wordle_hard(activator, context)
    else:
        await wordle_easy(activator, context)

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
    
async def update_wordle_leaderboard(activator: Neighbor, context: Context, seconds_to_solve, num_guesses):
    current_month = datetime.datetime.now(datetime.timezone.utc).month
    
    leaderboard = commands.remember("wordle_leaderboard")
    
    try:
        if current_month != leaderboard["month"]:
            commands.remember("wordle_leaderboard", delete=True)
            
            leaderboard = {
                "month": current_month,
                "leaderboard": [] #0 is best; #9 is worst
            }
    except:
        leaderboard = {
            "month": current_month,
            "leaderboard": [] #0 is best; #9 is worst
        }
        
        
    new_leaderboard_entry = {
        "member_id": activator.ID,
        "num_guesses": num_guesses,
        "seconds_to_solve": seconds_to_solve
    }

    new_leaderboard = leaderboard["leaderboard"].copy()
    new_leaderboard.append(new_leaderboard_entry)

    new_leaderboard.sort(
        key=lambda entry: (
            entry["num_guesses"],
            entry["seconds_to_solve"]
        )
    )

    new_leaderboard = new_leaderboard[:10]

    broke_into_leaderboard = new_leaderboard_entry in new_leaderboard
        
    leaderboard["leaderboard"] = new_leaderboard
    commands.remember("wordle_leaderboard", leaderboard)
        
    if broke_into_leaderboard:
        if commands.chance(5):
            await context.send("**🥇 I think I could have done better personally, but you've broken into the top 10 Wordle Solvers this month regardless! 🎉 `$wordle_leaderboard` to see!**")
        else:
            await context.send("**🥇 Wowzers! You've broken into the top 10 Wordle solvers this month! 🎉 `$wordle_leaderboard` to see!**")
            
@command_handler.Command(access_type=AccessType.PUBLIC, desc="View top 10 Wordle solvers this month!")
async def wordle_leaderboard(activator: Neighbor, context: Context):
    guild = context.guild
    
    wordle_leaderboard = commands.remember("wordle_leaderboard")
    
    current_month = datetime.datetime.now(datetime.timezone.utc).month
    if current_month != wordle_leaderboard["month"]:
        res = "Wow! It seems that no one has played Wordle yet this month!\n"
        res += "🏆 **Wordle Leaderboard for last month!**\n```"
    else:
        res = "🏆 **Wordle Leaderboard for this month!**\n```"
    res += f"{'#':<4}{'Player':<16}{'Guesses':<10}{'Time':<10}\n"

    for i, leaderboard_entry in enumerate(wordle_leaderboard["leaderboard"]):
        member_id = leaderboard_entry["member_id"]
        try:
            member = await guild.fetch_member(member_id)
            name = member.display_name
        except:
            name = "Unknown"
            
        if i == 0:
            champion = member_id
        else:
            if champion != member_id:
                champion = None;
            
        num_guesses = leaderboard_entry["num_guesses"]
        seconds_to_solve = leaderboard_entry["seconds_to_solve"]
        
        res += f"{i+1:<4}{name:<16}{num_guesses:<10}{seconds_to_solve:.2f}s\n"
        
    res += "```"
        
    await context.send(res, reply=True)
    if champion:
        await context.send(f"**WOAH! {name} has swept the leaderboard! Well done!! 🎉🎉🎉**")