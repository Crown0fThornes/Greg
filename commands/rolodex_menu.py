"""Owner-bound Council menus using ResponseRequest reactions and reply prompts."""
import copy
import json

import discord
from command_handler import Context
from id_bundle import FF
from responses import ResponseRequest
from persistence.sqlite_db import connect
from persistence.rolodex import FF_GUILD
from persistence.rolodex_records import FIELDS, records

TIMEOUT=600
HOME={'🧪':'Trial import (up to 50 recent messages)','⏬':'Start / resume historical import','🕒':'Import progress','⏹️':'Stop import','🔎':'View a profile','📋':'Review historical reports','📝':'Add a Council note',
      '🔗':'Connect accounts','🔓':'Disconnect accounts','✏️':'Correct a record',
      '➕':'Add a missing event','🗒️':'Edit / restore a note','↩️':'Reset a correction','🗑️':'Delete a note',
      '📜':'Audit history','ℹ️':'Command help','❌':'Close'}
FLOWS={
    '🔎':('profile',['Person: reply with a user mention or Discord ID.']),
    '📝':('note',['Person: reply with a user mention or Discord ID.','What should the Council note say?']),
    '🔗':('link',['Old account: mention or Discord ID?','New account: mention or Discord ID?','Why are these accounts being connected?']),
    '🔓':('unlink',['Old account: mention or Discord ID?','New account: mention or Discord ID?','Why are you disconnecting these accounts?']),
    '✏️':('edit',['Record type: name, membership, event, or manual?','Record key? Find it with the historical-review menu or $rolodex raw @user.','Field to correct?','New value? Use null for an unknown/cleared value.','Reason for the correction?']),
    '➕':('add',['Person: mention or Discord ID?','Is this a join or leave?','Which neighborhood? FFP, FFM, FFJ, FFJ2, FFG, FFC, or FFR.','Date? YYYY-MM-DD, optionally with a time and timezone.','Reason or source link?']),
    '↩️':('reset',['Record type: name, membership, event, or manual?','Record key?','Which field should return to its original value?','Reason for resetting it?']),
    '🗒️':('edit_note',['Note ID?','Updated note text?','Reason for editing / restoring it?']),
    '🗑️':('delete_note',['Note ID? Shown as #number beside the note.','Reason for deleting the note?']),
}


def safe(value):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(str(value)))


def authorized(context,user,owner):
    return (context.guild.id==FF_GUILD and user is not None and user.id==owner
            and (user.id==355169964027805698 or FF.leaders_role in [r.id for r in user.roles]))


def clear_requests(state):
    ResponseRequest.active_requests[:]=[r for r in ResponseRequest.active_requests
                                       if r.values.get('menu_session') is not state]


async def render(state,body,choices):
    clear_requests(state)
    message=state.get('message')
    content='**Rolodex Council menu**\n'+body+'\n\n'+ '\n'.join(f'{emoji} {label}' for emoji,label in choices.items())
    content+='\n\nOnly the Council member who opened this menu can use it. Expires after 10 minutes of inactivity.'
    if message is not None:
        try:
            await message.clear_reactions()
            await message.edit(content=content,allowed_mentions=discord.AllowedMentions.none())
        except (discord.Forbidden,discord.NotFound):
            message=None
    if message is None:
        message=await state['context'].channel.send(content,allowed_mentions=discord.AllowedMentions.none())
    state['message']=message
    activation=Context(message)
    def key(context):
        return (context.message.id==message.id and str(context.emoji) in choices
                and authorized(context,context.user,state['owner']))
    ResponseRequest(on_reaction,'rolodex_menu','REACTION',activation,activation,key=key,
                    timeout=TIMEOUT,menu_session=state)
    for emoji in choices:
        await message.add_reaction(emoji)


async def prompt(state):
    clear_requests(state)
    question=state['questions'][len(state['answers'])]
    message=await state['context'].channel.send('**Rolodex — '+question+'**\nReply to this message with your answer. React ❌ to cancel.',
                                                allowed_mentions=discord.AllowedMentions.none())
    def key(context):
        reference=getattr(context.message,'reference',None)
        return (authorized(context,context.author,state['owner']) and reference is not None
                and reference.message_id==message.id)
    ResponseRequest(on_answer,'rolodex_answer','MESSAGE',state['context'],Context(message),
                    key=key,timeout=TIMEOUT,menu_session=state)
    def cancel_key(context):
        return (context.message.id==message.id and str(context.emoji)=='❌'
                and authorized(context,context.user,state['owner']))
    ResponseRequest(on_reaction,'rolodex_cancel','REACTION',Context(message),Context(message),
                    key=cancel_key,timeout=TIMEOUT,menu_session=state)
    await message.add_reaction('❌')


async def review(state):
    with connect(state['store'].path) as db:
        rows=records(db)['event']
    mode=state.get('review_mode',0)
    if mode in (0,1):
        from persistence.rolodex_identities import groups,similar_groups
        with connect(state['store'].path) as db:
            all_groups=groups(db,rows)
        queue=[g for g in all_groups if mode==1 or not g['confirmed']]
        choices={'◀️':'Previous identity','▶️':'Next identity','📚':'Cycle unreviewed / all identities / unparsed','🏠':'Main menu','❌':'Close'}
        if not queue:
            state['record']=None
            await render(state,'No identities to review in this view.',choices)
            return
        group=queue[state.get('index',0)%len(queue)]
        state['record']={'identity_group':group}
        candidates=safe(str(group['candidates']))[:200]
        variants=safe(', '.join(group['variants']))[:250]
        examples='\n'.join(f"{safe(r['subject'])[:60]}: {r['action']} {safe(r['label'])} — {r['occurred_at'][:10]}" for r in group['events'][:3])
        related='\n'.join(f"#{other['id']} {safe(other['label'])[:60]} ({score:.0%} similar; {len(other['events'])} events)" for score,other in similar_groups(group,all_groups)) or 'None'
        body=(f"**Historical person #{group['id']} — {len(group['events'])} events**\n"
              f"Variants: {variants}\nDiscord ID: {group['user_id'] or 'unknown'}; confirmed: {group['confirmed']}\n"
              f"Suggested accounts (unconfirmed): {candidates}\n{examples}\n**Possible matching groups**\n{related}")
        await render(state,body,{'💡':'Explain account suggestions','🔍':'Browse this person’s individual reports','🔗':'Link ALL reports to a Discord account',
                               '❔':'Confirm same person; Discord ID unknown','🔀':'Merge with another historical person',
                               '↩️':'Reopen for review',**choices})
        return
    elif mode==3:
        rows=[r for r in rows if r.get('identity_id')==state.get('group_filter')]
    elif mode==2:
        from persistence.import_membership_history import LINE
        rows=[]
        with connect(state['store'].path) as db:
            for source in db.execute('SELECT * FROM membership_log_message WHERE guild_id=?',(FF_GUILD,)):
                for number,line in enumerate(source['content'].splitlines(),1):
                    if line.strip() and not LINE.fullmatch(line.strip()):
                        rows.append(dict(source,subject=line,occurred_at=source['posted_at'],
                                         line_number=number,event_number=0,unparsed=True))
    rows.sort(key=lambda r:(r['occurred_at'],r['message_id'],r['line_number'],r['event_number']))
    choices={'◀️':'Previous','▶️':'Next','📚':'Cycle unresolved / all / unparsed reports','🏠':'Main menu','❌':'Close'}
    if not rows:
        state['record']=None
        await render(state,'No reports in this view. Toggle to all reports, or return to the main menu.',choices)
        return
    index=state.get('index',0)%len(rows)
    state['index']=index
    row=rows[index]
    state['record']=row
    if row.get('unparsed'):
        link=f"https://discord.com/channels/{FF_GUILD}/{row['channel_id']}/{row['message_id']}"
        state['source_link']=link
        body=f"**Unparsed report {index+1}/{len(rows)}**\n{safe(row['subject'])[:700]}\n{link}"
        await render(state,body,{'➕':'Record an event from this source',**choices})
        return
    body=(f"**Historical report {index+1}/{len(rows)}**\n{safe(row['subject'])[:200]}: {row['action']} {safe(row['label'])}\n"
          f"Date: {safe(row['occurred_at'])}\nLinked user ID: {row['user_id'] or 'unresolved'}\n"
          f"Suggested IDs (unconfirmed): {safe(row['candidates'])[:200]}\n"
          f"https://discord.com/channels/{FF_GUILD}/{row['channel_id']}/{row['message_id']}")
    choices={'🔍':'Inspect original evidence','🔗':'Link / correct person','✏️':'Correct a field',
             '🚫':'Hide mistaken report','✂️':'Split this event into a separate person',**choices}
    await render(state,body,choices)


async def begin_flow(state,action,questions,*,prefix=None):
    state.pop('source_link',None)
    state.update(screen='form',action=action,questions=questions,answers=[],prefix=prefix or [])
    await prompt(state)


async def on_reaction(neighbor,activation,response):
    state=response.values['menu_session']
    clear_requests(state)
    member=state['context'].guild.get_member(state['owner'])
    if not authorized(state['context'],member,state['owner']):
        return
    choice=str(response.content)
    if choice=='❌':
        await state['context'].channel.send('Rolodex menu closed.',allowed_mentions=discord.AllowedMentions.none())
        return
    if choice=='🏠':
        state['screen']='home'
        await render(state,'Choose what you’d like to do.',HOME)
    elif state['screen']=='confirm':
        if choice=='✅':
            await execute(state)
    elif state['screen']=='review':
        row=state.get('record')
        if choice in ('◀️','▶️','📚'):
            if choice=='📚':
                state['review_mode']=(state.get('review_mode',0)+1)%3
                state['index']=0
            else:
                state['index']=state.get('index',0)+(1 if choice=='▶️' else -1)
            await review(state)
        elif row:
            if row.get('identity_group'):
                group=row['identity_group']
                if choice=='💡':
                    await invoke(state,['suggest',str(group['id'])])
                    await review(state)
                elif choice=='🔍':
                    state.update(review_mode=3,group_filter=group['id'],index=0)
                    await review(state)
                elif choice=='🔗':
                    await begin_flow(state,'identity',['Discord account mention or ID?','Reason confirming these reports belong to this account?'],prefix=['link',str(group['id'])])
                elif choice=='❔':
                    await begin_flow(state,'identity',['Reason confirming these reports belong to one person (Discord ID remains unknown)?'],prefix=['unknown',str(group['id'])])
                elif choice=='🔀':
                    await begin_flow(state,'identity',['Other historical identity number? See possible matches above.','Why are these the same person?'],prefix=['merge',str(group['id'])])
                elif choice=='↩️':
                    await begin_flow(state,'identity',['Why should this person be reviewed again?'],prefix=['reopen',str(group['id'])])
                return
            if choice=='✂️':
                await begin_flow(state,'identity',['Why should this event belong to a separate person?'],prefix=['split',row['record_key']])
            elif choice=='➕' and row.get('unparsed'):
                source=state['source_link']
                action,questions=FLOWS['➕']
                await begin_flow(state,action,questions)
                state['source_link']=source
            elif choice=='🔍':
                await invoke(state,['inspect','event',row['record_key']])
                await review(state)
            elif choice=='🔗':
                await begin_flow(state,'edit',['Who does this report describe? Mention or user ID.','Reason / evidence confirming this identity?'],prefix=['event',row['record_key'],'user_id'])
            elif choice=='🚫':
                await begin_flow(state,'edit',['Why should this report be hidden?'],prefix=['event',row['record_key'],'excluded','true'])
            elif choice=='✏️':
                state['screen']='field'
                state['field_choices']=dict(zip(('1️⃣','2️⃣','3️⃣','4️⃣','5️⃣'),sorted(FIELDS['event'])))
                await render(state,'Choose the field to correct.',{**state['field_choices'],'🏠':'Main menu','❌':'Close'})
    elif state['screen']=='field':
        field=state['field_choices'].get(choice)
        if field:
            await begin_flow(state,'edit',[f'New {field}?','Reason for this correction?'],prefix=['event',state['record']['record_key'],field])
    elif choice in ('⏬','🧪'):
        state.update(screen='confirm',action='import',prefix=['test'] if choice=='🧪' else [],answers=[])
        await render(state,'Import up to 25 newest messages per channel for review? Full-import checkpoints stay unchanged.' if choice=='🧪' else 'Start / resume the paced historical import? Progress updates will appear in this channel.',{'✅':'Start import','🏠':'Main menu','❌':'Cancel'})
    elif choice in ('🕒','⏹️'):
        await invoke(state,['import','status' if choice=='🕒' else 'stop'])
        await render(state,'Choose another action.',HOME)
    elif choice=='📋':
        state.update(screen='review',index=0)
        await review(state)
    elif choice in FLOWS:
        action,questions=FLOWS[choice]
        await begin_flow(state,action,questions)
    elif choice in ('📜','ℹ️'):
        await invoke(state,['audit' if choice=='📜' else 'help'])
        await render(state,'Use the page number shown in the response for additional pages, or choose another action.',HOME)


async def on_answer(neighbor,activation,response):
    state=response.values['menu_session']
    clear_requests(state)
    member=state['context'].guild.get_member(state['owner'])
    if not authorized(state['context'],member,state['owner']):
        return
    answer=str(response.content).strip()
    if not answer or len(answer)>1000:
        await state['context'].channel.send('Please enter 1–1000 characters.',allowed_mentions=discord.AllowedMentions.none())
        await prompt(state)
        return
    state['answers'].append(answer)
    if len(state['answers'])<len(state['questions']):
        await prompt(state)
    else:
        state['screen']='confirm'
        preview='\n'.join(f'{safe(question)}\n{safe(value)}' for question,value in zip(state['questions'],state['answers']))
        # Keep previews within Discord's limit; all full answers are retained in state.
        await render(state,'**Confirm your selection**\n'+preview[:1150],{'✅':'Confirm','🏠':'Discard and return','❌':'Cancel'})


async def invoke(state,args):
    from .rolodex import rolodex
    context=copy.copy(state['context'])
    context.args=args
    await rolodex(None,context)


async def execute(state):
    from .rolodex import uid
    args=state['prefix']+state['answers']
    action=state['action']
    try:
        if action in ('profile','note','add'):
            args[0]=str(uid(args[0]))
        elif action in ('link','unlink'):
            args[:2]=[str(uid(value)) for value in args[:2]]
        elif action=='identity' and args[0]=='link':
            args[2]=str(uid(args[2]))
        elif action=='edit' and len(args)>3 and args[2]=='user_id' and args[3].lower()!='null':
            args[3]=str(uid(args[3]))
        if action=='add' and state.get('source_link'):
            args[-1]+=' '+state['source_link']
        if action=='profile':
            command_args=args
        elif action=='delete_note':
            command_args=['note','delete',*args]
        elif action=='edit_note':
            command_args=['note','edit',*args]
        else:
            command_args=[action,*args]
        await invoke(state,command_args)
    except (ValueError,TypeError) as error:
        await state['context'].channel.send(safe(error),allowed_mentions=discord.AllowedMentions.none())
    state['screen']='home'
    await render(state,'Choose another action. Any saved correction includes your ID and reason.',HOME)


async def open_menu(context,store,*,review_mode=False):
    state={'context':context,'store':store,'owner':context.author_id,'screen':'review' if review_mode else 'home'}
    if review_mode:
        await review(state)
    else:
        await render(state,'Choose what you’d like to do.',HOME)
