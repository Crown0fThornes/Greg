"""Paced, resumable import of a year's welcome messages for recruitment averages."""
import asyncio
import calendar
from datetime import datetime, timedelta, timezone
import json
import logging
import time

import discord

from commands.recruitment_review import GENERAL, GUILD_ID, PATH, ST, connect, previous_week, welcome_user

tasks = {}
control_lock = asyncio.Lock()
log = logging.getLogger(__name__)


def window(now):
    today = now.astimezone(ST).replace(hour=0, minute=0, second=0, microsecond=0)
    year = today.year-1
    earliest = today.replace(year=year, day=min(today.day,calendar.monthrange(year,today.month)[1]))
    # Partial weeks skew daily/weekly means. Import only full Monday–Sunday weeks.
    start = earliest+timedelta(days=(-earliest.weekday())%7)
    _, end = previous_week(now)
    return start, end


def load(path):
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS baseline_import (id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL)')
        row = db.execute('SELECT state FROM baseline_import WHERE id=1').fetchone()
    return json.loads(row[0]) if row else None


def save(path, state):
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS baseline_import (id INTEGER PRIMARY KEY CHECK(id=1), state TEXT NOT NULL)')
        db.execute('INSERT INTO baseline_import VALUES (1,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state',
                   (json.dumps(state),))


def new_state(now):
    start, end = window(now)
    counts = {}
    day = start
    while day < end:
        counts[day.date().isoformat()] = [0]*7
        day += timedelta(days=7)
    return dict(start=start.isoformat(), end=end.isoformat(), cursor=0, scanned=0,
                recruits=0, counts=counts, status='running', through=None)


def summary(state):
    heading = f"**Recruitment baseline — {state['status']}**"
    lines = [heading, f"Period: {state['start'][:10]} through {state['end'][:10]} (end exclusive; ST)",
             f"Messages scanned: {state['scanned']:,} · Recruits found: {state['recruits']:,}",
             f"Complete weeks: {len(state['counts'])}"]
    if state.get('through'):
        lines.append(f"Scanned through: {state['through'][:10]} (ST)")
    if state['status']=='complete':
        lines.append('Baseline saved! Future Monday reviews will use these averages automatically.')
    else:
        lines.append('Runs in the background. Check `$recruitmentbaseline status` or pause with `$recruitmentbaseline stop`.')
    return '\n'.join(lines)


async def update(message, state):
    try:
        await message.edit(content=summary(state), allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        log.warning('Could not update recruitment baseline progress message')


async def scan(guild, bot_id, state, *, path=PATH, progress=None, pause=0.5):
    """Checkpoint each page before yielding; publish baseline only on completion."""
    channel = await guild.fetch_channel(GENERAL)
    start, end = datetime.fromisoformat(state['start']), datetime.fromisoformat(state['end'])
    updated = time.monotonic()
    while True:
        after = discord.Object(id=state['cursor']) if state['cursor'] else start-timedelta(microseconds=1)
        batch = [message async for message in channel.history(limit=100, after=after, before=end, oldest_first=True)]
        if not batch:
            break
        previous_cursor = state['cursor']
        for message in batch:
            if message.id <= state['cursor']:
                continue
            state['cursor'] = message.id
            state['scanned'] += 1
            local = message.created_at.astimezone(ST)
            state['through'] = local.isoformat()
            if start <= message.created_at < end and welcome_user(message, bot_id) is not None:
                monday = (local-timedelta(days=local.weekday())).date().isoformat()
                state['counts'][monday][local.weekday()] += 1
                state['recruits'] += 1
        if state['cursor'] == previous_cursor:
            raise RuntimeError('History scan did not advance; refusing to repeat a page')
        save(path,state)
        if progress and time.monotonic()-updated >= 30:
            await progress(state)
            updated = time.monotonic()
        await asyncio.sleep(pause)
    # Historical totals are committed all at once. Failed or partial scans never
    # introduce incomplete weeks into the live averages. Reimports replace counts.
    state['status'] = 'complete'
    with connect(path) as db:
        db.executemany('INSERT INTO baseline_week VALUES (?,?) ON CONFLICT(start) DO UPDATE SET counts=excluded.counts',
                       [(week,json.dumps(counts)) for week,counts in state['counts'].items()])
        db.execute('UPDATE baseline_import SET state=? WHERE id=1',(json.dumps(state),))


async def run(context, state, message, *, path=PATH):
    try:
        await scan(context.guild,context.guild.me.id,state,path=path,
                   progress=lambda current:update(message,current))
    except asyncio.CancelledError:
        # The previous page checkpoint is authoritative, including its counts.
        state = load(path)
        state['status'] = 'paused — run $recruitmentbaseline to resume'
        save(path,state)
    except Exception:
        log.exception('Recruitment baseline import failed')
        state = load(path)
        state['status'] = 'failed — run $recruitmentbaseline to resume; check bot logs'
        save(path,state)
    finally:
        await update(message,state)


async def control(context, action='', *, path=PATH, now=None):
    if context.guild.id != GUILD_ID:
        await context.send('Use this command in FF.')
        return
    async with control_lock:
        task = tasks.get(context.guild.id)
        active = task is not None and not task.done()
        state = load(path)
        if action=='status':
            if state and not active and state['status']=='running':
                state['status'] = 'not running — run $recruitmentbaseline to resume'
            await context.send(summary(state) if state else 'No baseline import has run yet. Use `$recruitmentbaseline` to start.')
            return
        if action=='stop':
            if active:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    state = load(path)
                    state['status'] = 'paused — run $recruitmentbaseline to resume'
                    save(path,state)
                await context.send('Recruitment baseline scan paused. Use `$recruitmentbaseline` to resume.')
            else:
                await context.send('No recruitment baseline scan is running.')
            return
        if active:
            await context.send('A recruitment baseline scan is already running. Use `$recruitmentbaseline status` for progress.')
            return
        if state is None or state['status']=='complete':
            state = new_state(now or datetime.now(timezone.utc))
        state['status'] = 'running'
        save(path,state)
        message = await context.send(summary(state))
        tasks[context.guild.id] = asyncio.create_task(run(context,state,message,path=path))
