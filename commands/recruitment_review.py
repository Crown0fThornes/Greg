"""Weekly recruitment summaries from Greg's welcome messages, in fixed ST."""
import asyncio
import calendar
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import re
import sqlite3

import discord

GUILD_ID = 647883751853916162
GENERAL = 648223397205114910
RECRUITMENT = 792497521259315200
ST = timezone(timedelta(hours=-4))
PATH = Path(__file__).resolve().parent.parent / 'data/recruitment_review.sqlite3'
MIN_BASELINE_WEEKS = 4
lock = asyncio.Lock()
log = logging.getLogger(__name__)


def previous_week(now):
    today = now.astimezone(ST).replace(hour=0, minute=0, second=0, microsecond=0)
    end = today - timedelta(days=today.weekday())
    return end - timedelta(days=7), end


def welcome_user(message, bot_id):
    if message.author.id != bot_id:
        return None
    text = message.content.replace('**', '').strip()
    match = re.match(r"^Welcome to Town,\s*<@!?(\d+)>!", text)
    return int(match[1]) if match else None


def parse_schedule(content):
    schedule = {}
    for line in content.splitlines():
        line = line.replace('**', '').replace('__', '').strip()
        for weekday, day in enumerate(calendar.day_name):
            if re.match(rf'^{day}\b', line, re.I):
                users = list(dict.fromkeys(int(uid) for uid in re.findall(r'<@!?(\d+)>', line)))
                if users:
                    schedule[str(weekday)] = users
    return schedule


async def read_schedule(channel):
    # The daily recruitment reminder also uses the first pinned schedule.
    for message in await channel.pins():
        schedule = parse_schedule(message.content)
        if schedule:
            return schedule
    return {}


async def count_joins(channel, bot_id, start, end):
    counts = [0] * 7
    seen_messages = set()
    async for message in channel.history(limit=None, after=start-timedelta(microseconds=1),
                                          before=end, oldest_first=True):
        if message.id in seen_messages or not start <= message.created_at < end:
            continue
        seen_messages.add(message.id)
        if welcome_user(message, bot_id) is not None:
            counts[message.created_at.astimezone(ST).weekday()] += 1
        if len(seen_messages) % 100 == 0:
            await asyncio.sleep(0)
    return counts


def date_label(day):
    return f'{day.month}/{day.day}'


def report(start, counts, schedule, previous):
    total = sum(counts)
    title = f'**Weekly Recruitment Review · {date_label(start)}–{date_label(start+timedelta(days=6))}**'
    lines = [title, '']
    lift_best = set()

    def day_label(index):
        return f'{calendar.day_name[index]} ({date_label(start+timedelta(days=index))})'

    def congratulate(indices):
        for index in indices:
            posters = schedule.get(str(index), [])
            if posters:
                mentions = ', '.join(f'<@{uid}>' for uid in posters)
                lines.append(f'Congratulations to {mentions}, scheduled for {calendar.day_name[index]}’s ad! 🎉')
            else:
                lines.append(f'No scheduled poster was found for {calendar.day_name[index]}.')

    if len(previous) >= MIN_BASELINE_WEEKS:
        means = [sum(week[i] for week in previous)/len(previous) for i in range(7)]
        gains = [counts[i]-means[i] for i in range(7)]
        best_gain = max(gains)
        if best_gain > 0:
            best = [i for i, gain in enumerate(gains) if abs(gain-best_gain) < 1e-9]
            lift_best = set(best)
            lines.append('**🌟 Biggest lift above the weekday average**')
            for index in best:
                lines.append(f'{day_label(index)}: **{counts[index]} recruits**, '
                             f'**+{gains[index]:.1f}** above its usual {means[index]:.1f}.')
            congratulate(best)
        else:
            lines.append('No day exceeded its weekday average this week.')
        lines.append('')

    lines.append(f'**Total recruits: {total}**')
    if len(previous) >= MIN_BASELINE_WEEKS:
        average = sum(map(sum, previous))/len(previous)
        difference = total-average
        comparison = f'{difference:+.1f} recruits'
        if average:
            comparison += f' ({difference/average:+.0%})'
        lines.append(f'Compared with an average week of {average:.1f}: **{comparison}**.')

    if total:
        most = max(counts)
        best = [i for i, count in enumerate(counts) if count == most]
        lines += ['', f'**📈 Most recruits in a day: {most}**',
                  ', '.join(day_label(index) for index in best)]
        # Avoid repeating congratulations if the same day already led the lift.
        congratulate([index for index in best if index not in lift_best])
    else:
        lines += ['', 'No server joins were found in Greg’s welcome messages this week.']
    if len(previous) < MIN_BASELINE_WEEKS:
        lines += ['', f'Weekday and weekly averages will appear after {MIN_BASELINE_WEEKS} prior weeks '
                  f'are recorded ({len(previous)} so far).']
    else:
        lines += ['', f'Averages use {len(previous)} prior recorded weeks.']
    lines += ['', '-# Counts are server joins recorded by Greg’s welcome messages, including rejoins. '
              'Ad credit follows the pinned schedule; joins may come from other sources.']
    return '\n'.join(lines)


def pages(content):
    page = ''
    for line in content.splitlines():
        # Normal reports fit in one message; ties or several scheduled posters
        # can require more. Split safely even for an unusually long pin line.
        while len(line) > 1900:
            if page:
                yield page.rstrip()
                page = ''
            yield line[:1900]
            line = line[1900:]
        if len(page)+len(line)+1 > 1900:
            yield page.rstrip()
            page = ''
        page += line+'\n'
    if page:
        yield page.rstrip()


@contextmanager
def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS week ('
                       'start TEXT PRIMARY KEY, counts TEXT NOT NULL, schedule TEXT NOT NULL, '
                       'content TEXT NOT NULL, status TEXT NOT NULL, message_id INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS baseline_week (start TEXT PRIMARY KEY, counts TEXT NOT NULL)')
            yield db
    finally:
        db.close()


async def review(client, *, now=None, path=PATH):
    async with lock:
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            return
        start, end = previous_week(now or datetime.now(timezone.utc))
        key = start.date().isoformat()
        with connect(path) as db:
            saved = db.execute('SELECT content,status FROM week WHERE start=?', (key,)).fetchone()
        if saved and saved[1] != 'ready':
            return
        target = await guild.fetch_channel(RECRUITMENT)
        if saved:
            content = saved[0]
        else:
            general = await guild.fetch_channel(GENERAL)
            counts = await count_joins(general, client.user.id, start, end)
            schedule = await read_schedule(target)
            with connect(path) as db:
                previous = prior_counts(db, key)
                content = report(start, counts, schedule, previous)
                db.execute("INSERT INTO week VALUES (?,?,?,?,'ready',NULL)",
                           (key, json.dumps(counts), json.dumps(schedule), content))
        with connect(path) as db:
            claimed = db.execute("UPDATE week SET status='pending' WHERE start=? AND status='ready'", (key,)).rowcount
        if not claimed:
            return
        try:
            # Only explicitly congratulated posters are pinged.
            recipients = list(dict.fromkeys(int(uid) for uid in re.findall(r'<@(\d+)>', content)))
            posted = None
            for page in pages(content):
                posted = await target.send(page, allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=[discord.Object(id=uid) for uid in recipients], replied_user=False))
        except (discord.Forbidden, discord.NotFound):
            if posted is None:
                with connect(path) as db:
                    db.execute("UPDATE week SET status='ready' WHERE start=?", (key,))
            raise
        except Exception:
            log.exception('Recruitment review delivery uncertain for %s; inspect pending row before retrying', key)
            raise
        else:
            with connect(path) as db:
                db.execute("UPDATE week SET status='sent',message_id=? WHERE start=?", (posted.id, key))


def prior_counts(db, key):
    # A normal weekly review takes precedence over an imported copy of that week.
    rows = dict(db.execute('SELECT start,counts FROM baseline_week WHERE start<?', (key,)))
    rows.update(db.execute('SELECT start,counts FROM week WHERE start<?', (key,)))
    return [json.loads(rows[start]) for start in sorted(rows)]
