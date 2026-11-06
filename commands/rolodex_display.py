"""Compact Rolodex presentation. Raw evidence stays in the database."""
from collections import defaultdict
from datetime import datetime
import re
import unicodedata
from zoneinfo import ZoneInfo

import discord
from discord.utils import escape_markdown, escape_mentions

INTRODUCTIONS_CHANNEL = 783713419831279697
TZ = ZoneInfo('America/New_York')


def clean(value):
    return escape_mentions(escape_markdown(str(value))).replace('\n', ' ')


def date_key(value):
    return datetime.fromisoformat(value).astimezone(TZ).date().isoformat()


def pretty_date(value):
    d = datetime.fromisoformat(value)
    if d.tzinfo:
        d = d.astimezone(TZ)
    n = d.day
    suffix = 'th' if 10 <= n % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(n % 10,'th')
    return f'{n}{suffix} {d.strftime("%B")}, {d.year}'


def label(value):
    return 'FFM' if value.upper() == 'FF' else value.upper()


def name_key(value):
    value = re.sub(r'[\[{][A-Za-z][\]}]', '', unicodedata.normalize('NFKC', value))
    return ''.join(ch.casefold() for ch in value if ch.isalnum())


def name_history(rows):
    # Prefer nicknames/global display names to account handles where available.
    shown, previous = [], None
    for row in sorted(rows, key=lambda r:(r['observed_at'],r['id'])):
        value = row['value']
        if not value:
            continue
        key = name_key(value)
        if not key or key == previous:
            continue
        shown.append(clean(value))
        previous = key
    return ' → '.join(shown) or 'No names recorded.'


def neighborhood_history(selected):
    events = []
    for kind in ('event','manual'):
        for row in selected[kind]:
            if row['kind'] == 'neighborhood':
                events.append((row['occurred_at'],row['action'],label(row['label']),True,False))
    for row in selected['membership']:
        if row['kind'] != 'neighborhood':
            continue
        events.append((row['started_at'] or row['first_observed_at'], 'join',label(row['label']),bool(row['started_at']),not bool(row['started_at'])))
        if row['ended_at'] or row['end_observed_at']:
            events.append((row['ended_at'] or row['end_observed_at'],'leave',label(row['label']),bool(row['ended_at']),False))
    days = defaultdict(list)
    for event in events:
        days[date_key(event[0])].append(event)
    active, output = {}, []
    for date, daily in sorted(days.items()):
        before = dict(active)
        # Duplicate live/imported reports count once. Baselines only establish unknown starts.
        verbs = defaultdict(set)
        for when,action,nh,known,baseline in sorted(daily, key=lambda event: event[0]):
            if action == 'join':
                if nh not in active:
                    active[nh] = when if known else None
            else:
                active.pop(nh,None)
            if not baseline:
                verbs[nh].add(action)
        neutral = {nh for nh,v in verbs.items() if v == {'join','leave'}}
        for nh in neutral:
            if nh in before:
                active[nh] = before[nh]
        joins = sorted(nh for nh,v in verbs.items() if nh not in neutral and 'join' in v)
        leaves = sorted(nh for nh,v in verbs.items() if nh not in neutral and 'leave' in v)
        if joins and leaves:
            output.append((date,f"• Switched from {clean(', '.join(leaves))} to {clean(', '.join(joins))} on {pretty_date(date)}",None))
        else:
            for nh in leaves:
                known = any(e[1]=='leave' and e[2]==nh and e[3] for e in daily)
                wording = f'on {pretty_date(date)}' if known else f'(date unknown; absence observed {pretty_date(date)})'
                output.append((date,f'• Previously left {clean(nh)} {wording}',None))
            for nh in joins:
                output.append((date,f'• Joined {clean(nh)} on {pretty_date(date)}',nh))
    # Show current last-known stays at the end; do not repeat their simple join line.
    current = set(active)
    final_joins = {}
    for index, (date,line,nh) in enumerate(output):
        if nh in current:
            final_joins[nh] = index
    lines = [line for i, (_,line,nh) in enumerate(output) if final_joins.get(nh) != i]
    for nh,since in sorted(active.items(),key=lambda pair:(pair[1] or '9999',pair[0])):
        lines.append(f'• In {clean(nh)} since {pretty_date(since)}' if since else f'• In {clean(nh)} (start date unknown)')
    return lines or ['• No neighborhood history recorded.']


def compact_profile(all_records, accounts, council_notes):
    selected = {kind:[r for r in rows if r['user_id'] in accounts and not r['excluded']]
                for kind,rows in all_records.items()}
    lines = ['**Neighborhood History**', *neighborhood_history(selected), '',
             '**Name History:** '+name_history(selected['name']), '',
             '**Link to introduction:** {introduction}', '', '**Council Notes:**']
    for note in council_notes:
        lines.append(f"- {clean(note['body'])} [added by {clean(note['added_by'])}] (#{note['note_id']})")
    if not council_notes:
        lines.append('- No Council notes yet.')
    return lines


async def find_introduction(guild, accounts):
    try:
        channel = await guild.fetch_channel(INTRODUCTIONS_CHANNEL)
        async for message in channel.history(oldest_first=False,limit=1000):
            if message.author.id in accounts and '#' in message.content and len(message.content)>99:
                return f'https://discord.com/channels/{guild.id}/{channel.id}/{message.id}'
        return 'Not found among the latest 1,000 introduction messages.'
    except (discord.Forbidden, discord.NotFound):
        return 'Unavailable — Greg cannot read the introductions channel.'
    except discord.HTTPException:
        return 'Temporarily unavailable.'
