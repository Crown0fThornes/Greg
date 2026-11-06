"""Paced, checkpointed Discord history imports with progress updates."""
import asyncio
import time

import discord
from persistence.import_membership_history import HistoryImporter,JOINLIST,LEAVELIST
from persistence.sqlite_db import connect

jobs={}


def summary(job):
    counts=job['counts']
    return (f"**Rolodex historical import — {job['status']}**\n"
            f"Source: {job.get('source','starting')}\n"
            f"Messages processed: {counts['messages']}\n"
            f"Parsed lines: {counts['resolved']+counts['unresolved']} "
            f"({counts['resolved']} with direct IDs; {counts['unresolved']} grouped for identity review)\n"
            f"Unparsed lines retained: {counts['unparsed_lines']}\n"
            'Paced at up to 5 messages/second; checkpoints survive restarts. '
            'Council reviews identities, not each individual report.')


async def update(job):
    try:
        await job['message'].edit(content=summary(job),allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        pass


async def run(context,store,job,*,full=False,test=False,pause=0.2):
    try:
        importer=await asyncio.to_thread(HistoryImporter,store,job['bot_id'])
        for member in context.guild.members:
            importer.add_member(member)
        for channel_id in (JOINLIST,LEAVELIST):
            job['source']=f'<#{channel_id}>'
            channel=await context.guild.fetch_channel(channel_id)
            with connect(store.path) as db:
                saved=db.execute('SELECT message_id FROM rolodex_import_cursor WHERE channel_id=?',(channel_id,)).fetchone()
            cursor=0 if full or test or saved is None else saved[0]
            options=dict(limit=25 if test else None,oldest_first=not test)
            if cursor:
                options['after']=discord.Object(id=cursor)
            processed=0
            async for message in channel.history(**options):
                if test and processed>=25:
                    break
                processed+=1
                # Yield SQLite/normalization work off the Discord event loop.
                counts=await asyncio.to_thread(importer.ingest,message)
                if not test:
                    with connect(store.path) as db:
                        db.execute('INSERT INTO rolodex_import_cursor VALUES (?,?) ON CONFLICT(channel_id) '
                                   'DO UPDATE SET message_id=MAX(message_id,excluded.message_id)',(channel_id,message.id))
                job['counts']['messages']+=1
                for key,value in counts.items():
                    job['counts'][key]+=value
                if time.monotonic()-job['updated']>=30:
                    await update(job)
                    job['updated']=time.monotonic()
                await asyncio.sleep(pause)
        job['status']='trial complete (up to 25 newest messages per channel)' if test else 'complete'
    except asyncio.CancelledError:
        job['status']='stopped — resume with $rolodex import'
    except Exception as error:
        job['status']=f'failed ({type(error).__name__}) — checkpoint saved; check bot logs'
        import logging
        logging.getLogger(__name__).exception('Rolodex background import failed')
    finally:
        await update(job)


async def control(context,store,args):
    key=context.guild.id
    current=jobs.get(key)
    option=args[0].lower() if args else 'start'
    if option=='status':
        await context.channel.send(summary(current) if current else 'No import has run in this bot session. Saved checkpoints will be used when you start one.',allowed_mentions=discord.AllowedMentions.none())
        return
    if option=='stop':
        if current and not current['task'].done():
            current['task'].cancel()
            await context.channel.send('Stopping the import after the current work item; committed checkpoints are retained.',allowed_mentions=discord.AllowedMentions.none())
        else:
            await context.channel.send('No import is running.',allowed_mentions=discord.AllowedMentions.none())
        return
    if option not in ('start','full','test'):
        raise ValueError('Use $rolodex import, import status, import stop, import test, or import full.')
    if current and not current['task'].done():
        await context.channel.send('An import is already running. Use $rolodex import status.',allowed_mentions=discord.AllowedMentions.none())
        return
    bot_id=context.guild.me.id
    # Build candidates from cached current members without a bulk fetch/chunk.
    # Name-history candidates are already loaded by HistoryImporter.
    notice='**Rolodex trial import starting…** Up to 25 newest messages per channel (50 total). Records are saved for review; full-import checkpoints are unchanged.' if option=='test' else '**Rolodex import starting…** Progress will update here every 30 seconds.'
    message=await context.channel.send(notice,allowed_mentions=discord.AllowedMentions.none())
    job=dict(message=message,status='running',counts=dict(messages=0,resolved=0,unresolved=0,unparsed_lines=0),updated=time.monotonic(),bot_id=bot_id)
    jobs[key]=job
    job['task']=asyncio.create_task(run(context,store,job,full=option=='full',test=option=='test'),name=f'rolodex-import-{key}')
