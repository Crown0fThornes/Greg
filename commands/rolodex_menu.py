"""Owner-bound Council menus using ResponseRequest reactions and reply prompts."""
import copy
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from command_handler import Context
from id_bundle import FF
from responses import ResponseRequest
from persistence.sqlite_db import connect
from persistence.rolodex import FF_GUILD
from persistence.rolodex_records import FIELDS, records
from .rolodex_mentions import prepare_mentions

TIMEOUT=600
HOME={'📋':'Review people','🔎':'View a profile','📝':'Council notes','🔗':'Account links','📥':'Import history','⚙️':'Other tools','❌':'Close'}
SECTIONS={
    '📝':('Council notes',{'📝':'Add note','🗒️':'Edit / restore note','🗑️':'Delete note','🏠':'Back','❌':'Close'}),
    '🔗':('Account links',{'🔗':'Connect old and new accounts','🔓':'Disconnect accounts','🏠':'Back','❌':'Close'}),
    '📥':('Historical import',{'🧪':'Try 50 recent messages','⏬':'Start / resume import','🕒':'Progress','⏹️':'Stop import','🏠':'Back','❌':'Close'}),
    '⚙️':('Other tools',{'✏️':'Correct a record','➕':'Add missing event','↩️':'Reset a correction','🏆':'Review leaderboard','📜':'Audit history','ℹ️':'Command help','🏠':'Back','❌':'Close'}),
}
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
    state['choices']=choices
    content='**Rolodex Council menu**\n'+body+'\n\n'+ '\n'.join(f'{emoji} {label}' for emoji,label in choices.items())
    content+='\n\nReact below to choose • Your session expires after 10 minutes.'
    content=await prepare_mentions(state['context'].guild,content)
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
    message=await state['context'].channel.send('**Rolodex — '+question+'**\nSend your answer here (or reply to this prompt). ❌ cancels.',
                                                allowed_mentions=discord.AllowedMentions.none())
    def key(context):
        reference=getattr(context.message,'reference',None)
        return (authorized(context,context.author,state['owner']) and (reference is None or reference.message_id==message.id)
                and not context.content.lstrip().startswith('$'))
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
        from persistence.rolodex_identities import richer_suggestions
        with connect(state['store'].path) as db:
            suggestions=richer_suggestions(db,group,all_groups)
        candidate_ids=list(dict.fromkeys([item['user_id'] for item in suggestions]+group['candidates']))
        state['candidate_ids']=candidate_ids
        state['suggestions']=suggestions
        state['related']=similar_groups(group,all_groups)
        name=safe(group['label'])[:100]
        linked=f"<@{group['user_id']}>" if group['user_id'] else 'Account not linked'
        examples='\n'.join(f"{safe(r['subject'])[:80]}: {r['action']} {safe(r['label'])} — {r['occurred_at'][:10]}" for r in group['events'][:3])
        body=f"**{name}** · {len(group['events'])} records · Person #{group['id']}\n{examples}"
        choices={}
        if len(candidate_ids)==1:
            body+=f"\n\n**Is this <@{candidate_ids[0]}>?**\n✅ confirms the match and opens the next person."
            choices['✅']='Yes, this is the suggested person'
        elif candidate_ids:
            body+='\n\nPossible accounts: '+', '.join(f'<@{uid}>' for uid in candidate_ids[:5])
            body+='\nChoose an account to confirm, or skip for now.'
        else:
            body+=f'\n\n{linked}. Choose an account, or skip for now.'
        choices['❔']='Unknown account — confirm this person'
        choices.update({'🔗':'Choose a different account' if len(candidate_ids)==1 else 'Choose an account',
                        '▶️':'Skip for now','💡':'See match evidence','⚙️':'More options','🏠':'Main menu'})
        if state.pop('notice',None):
            body='✅ Previous decision saved.\n\n'+body
        await render(state,body,choices)
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
    body=report_card(row,index,len(rows))
    candidates=json.loads(row['candidates'])
    choices={}
    if row['user_id'] is None and len(candidates)==1:
        choices['✅']='Confirm suggested person'
    choices.update({'🔗':'Choose person','◀️':'Previous','▶️':'Next','⚙️':'More options','🔙':'Back to people'})
    await render(state,body,choices)


def report_card(row,index,total):
    names={'FF':'Main (FFM)','FFM':'Main (FFM)','FFP':'Pro (FFP)','FFJ':'Junior (FFJ)',
           'FFJ2':'Junior 2 (FFJ2)','FFG':'Garden (FFG)','FFC':'Carnival (FFC)','FFR':'Resort (FFR)'}
    where='the server' if row['kind']=='server' else names.get(row['label'],row['label'])
    when=datetime.fromisoformat(row['occurred_at']).astimezone(ZoneInfo('America/New_York'))
    date=f"{when.strftime('%b')} {when.day}, {when.year}"
    verb='Joined' if row['action']=='join' else 'Left'
    body=f"**{safe(row['subject'])[:150]}** · Report {index+1} of {total}\n\n**{verb} {safe(where)}**\n{date}\n"
    if row['user_id']:
        body+=f"\nLinked to <@{row['user_id']}>\n"
    else:
        candidates=json.loads(row['candidates'])
        if len(candidates)==1:
            body+=f"\nIs this <@{candidates[0]}>? React ✅ to confirm.\n"
        elif candidates:
            body+='\nPossible people: '+', '.join(f'<@{uid}>' for uid in candidates[:3])+'\n'
    body+=f"\n[View original report](https://discord.com/channels/{FF_GUILD}/{row['channel_id']}/{row['message_id']})"
    return body


async def begin_flow(state,action,questions,*,prefix=None):
    state.pop('source_link',None)
    state.pop('auto_reason',None)
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
    elif state['screen']=='section':
        if choice in FLOWS:
            action,questions=FLOWS[choice]
            await begin_flow(state,action,questions)
        else:
            await home_action(state,choice)
    elif state['screen']=='report_tools':
        if choice=='🔙':
            state['screen']='review'
            await review(state)
        else:
            state['screen']='review'
            await on_reaction(neighbor,activation,response)
    elif state['screen'] in ('identity_tools','identity_details','account_pick','review_views'):
        await identity_choice(state,choice)
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
            if not row.get('identity_group') and choice=='🔙':
                state.update(screen='review',review_mode=0,index=0)
                await review(state)
                return
            if not row.get('identity_group') and choice=='⚙️':
                state['screen']='report_tools'
                await render(state,'**Report tools**',{'🔍':'Inspect full evidence','✏️':'Correct a detail','🚫':'Hide this report','✂️':'Separate into another person','🔙':'Back','❌':'Close'})
                return
            if not row.get('identity_group') and choice=='✅':
                candidates=json.loads(row['candidates'])
                if row['user_id'] is None and len(candidates)==1:
                    from persistence.rolodex_records import edit_record
                    edit_record(state['store'],'event',row['record_key'],'user_id',candidates[0],state['owner'],'Council confirmed suggested person in report menu')
                    state['index']=state.get('index',0)+1
                    await review(state)
                return
            if row.get('identity_group'):
                await identity_choice(state,choice)
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
                await begin_flow(state,'edit',['Mention the correct person (or send their Discord ID).'],prefix=['event',row['record_key'],'user_id'])
                state['auto_reason']='Council confirmed individual report identity in review menu'
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
    elif state['screen']=='home' and choice in SECTIONS:
        await section(state,choice)
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
    elif choice in ('📜','ℹ️','🏆'):
        await invoke(state,['leaderboard' if choice=='🏆' else 'audit' if choice=='📜' else 'help'])
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
    elif state['action'] in ('identity','edit') and state.get('auto_reason'):
        await execute(state)
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
        if state.get('auto_reason'):
            args.append(state.pop('auto_reason'))
        if action=='identity':
            await save_identity(state,args)
            return
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
    for request in list(ResponseRequest.active_requests):
        previous=request.values.get('menu_session')
        if previous and previous['owner']==context.author_id and previous['context'].channel.id==context.channel.id:
            clear_requests(previous)
    state={'context':context,'store':store,'owner':context.author_id,'screen':'review' if review_mode else 'home'}
    if review_mode:
        await review(state)
    else:
        await render(state,'Choose what you’d like to do.',HOME)


async def section(state,choice):
    title,choices=SECTIONS[choice]
    state['screen']='section'
    await render(state,'**'+title+'**\nChoose an action.',choices)


async def home_action(state,choice):
    # Reuse the existing command dispatcher for import/status/help actions.
    state['screen']='home'
    response=type('MenuAction',(),{'content':choice,'values':{'menu_session':state}})()
    await on_reaction(None,state['context'],response)


async def save_identity(state,args):
    from .rolodex import uid
    from persistence.rolodex_identities import change_identity
    operation,key=args[:2]
    value=None
    if operation in ('link','merge'):
        value=uid(args[2]) if operation=='link' else int(args[2])
        reason=' '.join(args[3:])
    else:
        reason=' '.join(args[2:])
    change_identity(state['store'],operation,key,value,state['owner'],reason)
    state.update(screen='review',review_mode=0,notice=True)
    await review(state)


async def identity_choice(state,choice):
    from .rolodex import uid
    group=state['record']['identity_group']
    key=str(group['id'])
    if choice=='🔙':
        state['screen']='review'
        await review(state)
        return
    if state['screen']=='account_pick':
        if choice in state.get('account_choices',{}):
            selected=state['account_choices'][choice]
            await save_identity(state,['link',key,str(selected),'Council confirmed selected account in reaction menu'])
        elif choice=='➕':
            await begin_flow(state,'identity',['Mention the correct person (or send their Discord ID).'],prefix=['link',key])
            state['auto_reason']='Council manually matched the historical person in Rolodex'
        return
    if state['screen']=='review_views':
        modes={'1️⃣':0,'2️⃣':1,'3️⃣':2}
        if choice in modes:
            state.update(screen='review',review_mode=modes[choice],index=0)
            await review(state)
        elif choice=='◀️':
            state.update(screen='review',index=state.get('index',0)-1)
            await review(state)
        return
    if choice=='✅' and len(state.get('candidate_ids',[]))==1:
        await save_identity(state,['link',key,str(state['candidate_ids'][0]),'Council confirmed suggested account in reaction menu'])
    elif choice=='🔗':
        candidates=state.get('candidate_ids',[])[:3]
        state['account_choices']=dict(zip(('1️⃣','2️⃣','3️⃣'),candidates))
        choices={emoji:f'Confirm <@{account}>' for emoji,account in state['account_choices'].items()}
        choices.update({'➕':'Someone else','🔙':'Back','❌':'Close'})
        state['screen']='account_pick'
        await render(state,'**Choose the correct person**\nSelecting an account saves the match and moves to the next person.',choices)
    elif choice=='💡':
        lines=[]
        for suggestion in state.get('suggestions',[])[:2]:
            lines.append(f"**<@{suggestion['user_id']}>**")
            lines.extend('• '+safe(reason)[:200] for reason in suggestion['reasons'][:2])
            lines.extend('⚠ '+safe(reason)[:160] for reason in suggestion['conflicts'][:1])
        state['screen']='identity_details'
        await render(state,'**Why Greg suggested this match**\n'+('\n'.join(lines)[:1050] or 'No account evidence yet.'),{'✅':'Confirm suggested person','🔗':'Choose account','🔙':'Back','❌':'Close'} if len(state.get('candidate_ids',[]))==1 else {'🔗':'Choose account','🔙':'Back','❌':'Close'})
    elif choice=='⚙️':
        state['screen']='identity_tools'
        await render(state,'**More options for '+safe(group['label'])[:80]+'**',{'🔍':'Individual reports','❔':'Confirm person, account unknown','🔀':'Merge another name group','↩️':'Reopen this identity','📚':'Review filters / previous person','🔙':'Back','❌':'Close'})
    elif choice=='❔':
        await save_identity(state,['unknown',key,'Council confirmed one historical person; Discord account unknown'])
    elif choice=='🔀':
        related='\n'.join(f"#{other['id']}: {safe(other['label'])[:60]}" for _,other in state.get('related',[])[:3])
        await begin_flow(state,'identity',['Which other historical person number? '+related],prefix=['merge',key])
        state['auto_reason']='Council confirmed same person across name groups'
    elif choice=='↩️':
        await save_identity(state,['reopen',key,'Council reopened identity in review menu'])
    elif choice=='🔍':
        state.update(screen='review',review_mode=3,group_filter=group['id'],index=0)
        await review(state)
    elif choice=='📚':
        state['screen']='review_views'
        await render(state,'**Choose what to review**',{'1️⃣':'People needing review','2️⃣':'All historical people','3️⃣':'Unparsed reports','◀️':'Previous person','🔙':'Back','❌':'Close'})
