"""Provisional profile history with explicit Council reaction confirmation."""
from difflib import SequenceMatcher
import discord
from command_handler import Context
from responses import ResponseRequest
from persistence.sqlite_db import connect
from persistence.rolodex_identities import groups,richer_suggestions,stripped_name,change_identity
from persistence.rolodex_records import records
from .rolodex_menu import authorized,safe

NUMBERS=('1️⃣','2️⃣','3️⃣')


def profile_matches(db,all_records,accounts,current_names=()):
    all_groups=groups(db,all_records['event'])
    names={stripped_name(value) for value in current_names if value}
    names.update(stripped_name(r['value']) for r in all_records['name'] if r['user_id'] in accounts and r['value'] and not r['excluded'])
    names.discard('')
    found=[]
    for group in all_groups:
        if group['confirmed']:
            continue
        pending=[r for r in group['events'] if r['user_id'] is None and not r['excluded']]
        if not pending:
            continue
        evidence=richer_suggestions(db,group,all_groups)
        matching=[item for item in evidence if item['user_id'] in accounts]
        strength=max((item['strength'] for item in matching),default=0)
        score=max((SequenceMatcher(None,group['normalized_name'].replace(' ',''),name.replace(' ','')).ratio()
                   for name in names if len(name.replace(' ',''))>=4 and len(group['normalized_name'].replace(' ',''))>=4),default=0)
        exact=group['normalized_name'] in names and len(group['normalized_name'].replace(' ',''))>=3
        if not matching and not exact and score<0.85:
            continue
        reason='Recorded-name match' if strength>=3 or exact else 'Similar name — not confirmed'
        if any(item['user_id'] not in accounts and item['strength']>=strength for item in evidence):
            reason+='; other accounts may also match'
        found.append(dict(group=group,events=pending,reason=reason,strength=max(strength,3 if exact else 1),score=score))
    return sorted(found,key=lambda item:(-item['strength'],-item['score'],item['group']['id']))


def suggestion_lines(matches):
    if not matches:
        return [],{}
    lines=['','**Possible historical records — needs Council confirmation**',
           'These are suggestions, separate from confirmed history. React to confirm a group belongs to this profile.']
    choices={}
    for number,item in zip(NUMBERS,matches):
        group=item['group']
        choices[number]=group['id']
        examples='; '.join(f"{r['action']} {safe(r['label'])} {r['occurred_at'][:10]}" for r in item['events'][:3])
        lines.append(f"**{number} {safe(group['label'])[:80]}** — {len(item['events'])} records\n{item['reason']}\n{examples}")
    if len(matches)>len(NUMBERS):
        lines.append('More possible groups are available through $rolodex review.')
    return lines,choices


def bind(context,store,message,choices,target):
    # Only expose confirmations for groups actually visible on this page.
    visible={emoji:key for emoji,key in choices.items() if f'**{emoji} ' in message.content}
    if not visible:
        return
    activation=Context(message)
    def key(ctx):
        return ctx.message.id==message.id and str(ctx.emoji) in visible and authorized(ctx,ctx.user,context.author_id)
    ResponseRequest(confirm,'rolodex_profile_match','REACTION',activation,activation,key=key,timeout=600,
                    context=context,store=store,message=message,choices=visible,target=target)
    return visible


async def confirm(neighbor,activation,response):
    values=response.values
    context=values['context']
    if not authorized(context,context.guild.get_member(context.author_id),context.author_id):
        return
    group_id=values['choices'].get(str(response.content))
    if group_id is None:
        return
    store=values['store']
    with connect(store.path) as db:
        current=next((g for g in groups(db,records(db)['event']) if g['id']==group_id),None)
    if current is None or current['confirmed']:
        await context.channel.send('That historical person was already reviewed. Reopen the profile to refresh.',allowed_mentions=discord.AllowedMentions.none())
        return
    change_identity(store,'link',str(group_id),values['target'],context.author_id,'Council confirmed provisional history from account profile')
    emoji=str(response.content)
    content=values['message'].content.replace(f'**{emoji} ',f'**✅ Confirmed — ',1)
    await values['message'].edit(content=content,allowed_mentions=discord.AllowedMentions.none())
    values['message'].content=content
    remaining={k:v for k,v in values['choices'].items() if k!=emoji}
    visible=bind(context,store,values['message'],remaining,values['target'])
    if visible:
        for reaction in visible:
            await values['message'].add_reaction(reaction)
