"""Restore persistent private voting menus and repair older expiring ballots."""
import asyncio
from datetime import datetime, timezone
import re

import discord


async def draft_view(row,uid,store,message):
    from commands.council_election import BallotView, candidates
    text=message.content
    for attachment in message.attachments:
        if attachment.filename==f"draft-{row['id']}.txt":
            text=(await attachment.read()).decode('utf-8')
            break
    match=re.search(rf"DRAFT-V1:{row['id']}:(\d+):([\d,]*)\|\|",text)
    if not match:
        raise ValueError('Draft checkpoint is missing')
    ranking=[int(uid) for uid in match[2].split(',') if uid]
    if len(set(ranking))!=len(ranking) or not set(ranking)<=set(candidates(row)):
        raise ValueError('Draft checkpoint contains invalid candidates')
    view=BallotView(row,uid,store)
    view.ranking=ranking
    view.page=int(match[1])
    view.refresh()
    return view


async def restore(client,row,store):
    from commands.council_election import BallotEntryView, registered_menus, track_menu
    now=datetime.now(timezone.utc).timestamp()
    if row['status']!='open' or row['config']['deadline']<=now:
        return
    # Only message references are local; rankings stay in the Discord DM.
    for saved in store.menus(row['id']):
        identity=(str(store.path),saved['message_id'])
        if identity in registered_menus:
            continue
        try:
            channel=client.get_channel(saved['dm_id']) or await client.fetch_channel(saved['dm_id'])
            if channel.recipient.id!=saved['user_id']:
                continue
            message=await channel.fetch_message(saved['message_id'])
            if message.author.id!=client.user.id:
                continue
            if saved['kind']=='draft':
                try:
                    view=await draft_view(row,saved['user_id'],store,message)
                except ValueError:
                    view=BallotEntryView(row,saved['user_id'],store)
                    await message.edit(content=view.text(),view=view,attachments=[])
                    store.menu(row['id'],saved['user_id'],saved['dm_id'],saved['message_id'],'entry')
            else:
                view=BallotEntryView(row,saved['user_id'],store)
            client.add_view(view,message_id=message.id)
            registered_menus.add(identity)
        except discord.NotFound:
            store.forget_menu(saved['message_id'])
        except discord.HTTPException:
            continue

    # Old deployments did not retain menu IDs. Look back once per voter and
    # replace dead dropdowns with a durable entry button, without a DM blast.
    guild=client.get_guild(row['config']['guild_id'])
    if guild is None:
        return
    for uid in row['config']['voters']:
        if store.repaired(row['id'],uid):
            continue
        try:
            member=await guild.fetch_member(uid)
            channel=await member.create_dm()
            since=datetime.fromtimestamp(row['config']['created_at'],timezone.utc)
            async for message in channel.history(limit=None,after=since,oldest_first=True):
                if message.author.id!=client.user.id:
                    continue
                legacy=(f"**Private ballot — Election #{row['id']}:" in message.content or
                        any((getattr(item,'custom_id','') or '').startswith(f"election:{row['id']}:{uid}:")
                            for component in getattr(message,'components',[]) for item in component.children))
                if not legacy or (str(store.path),message.id) in registered_menus:
                    continue
                view=BallotEntryView(row,uid,store)
                if f"DRAFT-V1:{row['id']}:" in message.content or any(
                    attachment.filename==f"draft-{row['id']}.txt" for attachment in message.attachments
                ):
                    try:
                        view=await draft_view(row,uid,store,message)
                        client.add_view(view,message_id=message.id)
                        track_menu(store,row,uid,message,'draft')
                        continue
                    except ValueError:
                        pass
                await message.edit(content=view.text(),view=view,attachments=[])
                track_menu(store,row,uid,message,'entry')
            store.mark_repaired(row['id'],uid)
        except discord.NotFound:
            store.mark_repaired(row['id'],uid)
        except discord.HTTPException:
            continue
        await asyncio.sleep(0.1)
