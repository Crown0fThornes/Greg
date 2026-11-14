"""Private DM ballots for Council elections, without changing core dispatch."""
import asyncio
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import logging
import re
import io

import discord

from commands.election_count import count_stv, validate_ranking
from commands.election_store import ElectionStore

GUILD_ID=647883751853916162
COUNCIL_ROLE=648188387836166168
ST=timezone(timedelta(hours=-4))
lock=asyncio.Lock()
log=logging.getLogger(__name__)
registered_menus=set()
HELP='''**Council elections**
`$election create "Election name" seats month/day/year hour:minute AM/PM @candidate-or-role ...`
Choose any positive number of seats, with at least that many candidates. Times use ST (UTC−4).
Role mentions add all their non-bot members as candidates. Omitting seats defaults to 2.
Current Council members receive DM ballots immediately and reminders every 24 hours until submitted.
`$vote ID` — optional fallback to resend the DM invitation. Normal voting needs no server command.
`$election list` / `$election status ID` — elections and turnout, without interim tallies.
`$election close ID` — close early and count; normally closes automatically at its deadline.
`$election results ID` / `$election rounds ID` — aggregate results and count rounds.
`$election cancel ID` — cancel an open election.
Tied seats remain unfilled for a Senior Member vote. No random tie-breaks.'''


def safe(text):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text.replace('\n',' ')[:100]))


def candidates(row):
    return [candidate['id'] for candidate in row['config']['candidates']]


def seat_count(row):
    return row['config'].get('seats',2)


def name(row,uid):
    return next(safe(candidate['name']) for candidate in row['config']['candidates'] if candidate['id']==uid)


def open_for(row,uid,now):
    if uid not in row['config']['voters']:
        raise ValueError('You are not on this election’s Council voter list.')
    if row['status']!='open' or now>=row['config']['deadline']:
        raise ValueError('This election is no longer accepting ballots.')


def receipt_content(row,ranking):
    lines=[f"**Ballot receipt — Election #{row['id']}: {safe(row['config']['title'])}**"]
    lines.extend(f'{index}. {name(row,uid)}' for index,uid in enumerate(ranking,1))
    lines += ['', 'Your latest submitted receipt is your vote. Use '
              'the **Change my vote** button in this DM to replace it before closing.',
              'This receipt counts only after Greg confirms that your ballot was submitted.',
              f"BALLOT-V1:{row['id']}:"+','.join(map(str,ranking))]
    return '\n'.join(lines)


def read_receipt(message,row,bot_id):
    if message.author.id!=bot_id:
        raise ValueError('A saved ballot receipt was not authored by Greg; counting stopped.')
    match=re.search(rf"^BALLOT-V1:{row['id']}:(\d+(?:,\d+)*)$",message.content,re.M)
    if not match:
        raise ValueError('A saved ballot receipt is unreadable; counting stopped.')
    return validate_ranking([int(uid) for uid in match[1].split(',')],candidates(row),seat_count(row))


async def load_receipt(message,row,bot_id):
    if message.content.endswith(f"BALLOT-FILE-V1:{row['id']}"):
        if message.author.id!=bot_id:
            raise ValueError('A ballot receipt was not authored by Greg.')
        attachment=next((attachment for attachment in message.attachments
                         if attachment.filename==f"ballot-{row['id']}.txt"),None)
        if attachment is None:
            raise ValueError('A saved ballot attachment is missing; counting stopped.')
        text=(await attachment.read()).decode('utf-8')
        # Use the same validation for a long ballot's attached receipt.
        from types import SimpleNamespace
        return read_receipt(SimpleNamespace(author=message.author,content=text),row,bot_id)
    return read_receipt(message,row,bot_id)


def election_summary(row,store):
    config=row['config']
    submitted={voter['user_id'] for voter in store.receipts(row['id'])}
    missing=[uid for uid in config['voters'] if uid not in submitted]
    invitations=store.invitations(row['id'])
    blocked=[uid for uid in missing if invitations.get(uid,{}).get('status') in ('blocked','failed')]
    return (f"**Election #{row['id']}: {safe(config['title'])} — {row['status']}**\n"
            f"{seat_count(row)} seats · {len(config['candidates'])} candidates · {len(config['voters'])} eligible Council voters\n"
            f"Ballots submitted: {len(submitted)}\n"
            'Awaiting ballots: '+(', '.join(f'<@{uid}>' for uid in missing) or 'Nobody')+'\n'
            +('DM delivery needs attention: '+', '.join(f'<@{uid}>' for uid in blocked)+'\n' if blocked else '')+
            f"Closes: <t:{int(config['deadline'])}:F>\n"
            'Candidates: '+', '.join(name(row,uid) for uid in candidates(row))+'\n'
            'Council voters receive a DM with a **Start / continue voting** button that works until closing.\n'
            'Unsubmitted ballots receive a DM reminder every 24 hours until closing.\n'
            'Counting: STV, Droop quota, fractional surplus transfers. '
            'Tied final seats go to a Senior Member vote. Earlier elimination ties use prior-round totals; '
            'if those cannot resolve the tie, counting stops for Senior Member review.\n'
            'Ballot receipts stay in your DMs with Greg; Council sees aggregate results only.')


def results_text(row):
    result=row['result']
    if not result:
        return 'Results are not available yet. No interim candidate tallies are displayed.'
    lines=[f"**Election #{row['id']}: {safe(row['config']['title'])} — Results**",
           f"Valid ballots: {result['ballots']} · Seats: {seat_count(row)} · Quota: {result['quota']}"]
    for index,uid in enumerate(result['winners'],1):
        lines.append(f"**Elected: {name(row,uid)}** (<@{uid}>)")
    if result['tied']:
        lines += [f"**{result['unfilled']} seat(s) unresolved — Senior Member vote required.**",
                  'Still-contending candidates: '+', '.join(f'{name(row,uid)} (<@{uid}>)' for uid in result['tied'])]
        if result['rounds'][-1]['action']=='elimination_tie':
            lines.append('An unresolved elimination tie could affect the outcome; no candidate was eliminated arbitrarily.')
        else:
            lines.append('The remaining candidates are tied. No winner was chosen for the remaining seat(s).')
    elif not result['ballots']:
        lines.append('No ballots were submitted. No seats were filled.')
    lines.append(f"Council can see the count with `$election rounds {row['id']}`.")
    return '\n'.join(lines)


def round_text(row):
    result=row['result']
    if not result:
        return ['No results are available yet.']
    lines=[f"**Election #{row['id']} — counting rounds**",
           'Exact fractional arithmetic; displayed totals are rounded to three decimals.']
    labels=dict(elect='Elected',elect_remaining='Elected remaining',eliminate='Eliminated',
                tie='Final tie',elimination_tie='Unresolved elimination tie')
    for number,round_ in enumerate(result['rounds'],1):
        totals=', '.join(f'{name(row,int(uid))}: {float(Fraction(value)):.3f}' for uid,value in round_['totals'].items())
        lines += [f"**Round {number}**",totals,
                  f"Exhausted: {float(Fraction(round_['exhausted'])):.3f}",
                  labels[round_['action']]+': '+', '.join(name(row,uid) for uid in round_['candidates'])]
        if 'transfer' in round_:
            lines.append(f"Transferred {float(Fraction(round_['transfer'])):.3f} of each ballot’s current weight supporting that winner.")
    return lines


async def post_result(channel,row):
    content=results_text(row)
    if len(content)<=1900:
        return await channel.send(content,allowed_mentions=discord.AllowedMentions.none())
    file=discord.File(io.BytesIO(content.encode('utf-8')),filename=f"election-{row['id']}-results.txt")
    try:
        return await channel.send(f"**Election #{row['id']}: {safe(row['config']['title'])} — Results**\n"
            f"Elected: {len(row['result']['winners'])} · Unfilled seats: {row['result']['unfilled']}\n"
            'Full results are attached.'+(' A Senior Member vote is required for unresolved seats.' if row['result']['tied'] else ''),
            file=file,allowed_mentions=discord.AllowedMentions.none())
    finally:
        file.close()


async def send_lines(channel,lines):
    page=''
    for line in lines:
        while len(line)>1900:
            if page:
                await channel.send(page,allowed_mentions=discord.AllowedMentions.none())
                page=''
            await channel.send(line[:1900],allowed_mentions=discord.AllowedMentions.none())
            line=line[1900:]
        if len(page)+len(line)+1>1900:
            await channel.send(page,allowed_mentions=discord.AllowedMentions.none())
            page=''
        page+=line+'\n'
    if page:
        await channel.send(page,allowed_mentions=discord.AllowedMentions.none())


def track_menu(store,row,uid,message,kind):
    store.menu(row['id'],uid,message.channel.id,message.id,kind)
    registered_menus.add((str(store.path),message.id))


def ballot_introduction(row):
    seats=seat_count(row)
    positions='position' if seats==1 else 'positions'
    nominees='nominee' if seats==1 else 'nominees'
    return (f"# {safe(row['config']['title'])}\n\n"
            f"Voting is now open and ends <t:{int(row['config']['deadline'])}:F>.\n\n"
            'You will choose candidates in order of your preference (First pick = your top choice).\n\n'
            f'You are voting to fill **{seats} {positions}**.\n'
            f'You must rank at least **{seats} {nominees}** but are encouraged to rank as many as you approve of.\n\n'
            'Ranking more nominees does not dilute your vote for your top choices.\n\n'
            'It is your right to vote. If you have issues or are concerned your vote was not counted, '
            'please contact Lincoln.')


class BallotEntryView(discord.ui.View):
    """A durable entry point, including after submitting a ballot."""
    def __init__(self,row,uid,store):
        super().__init__(timeout=None)
        self.row=row
        self.uid=uid
        self.store=store
        button=discord.ui.Button(label='Start / continue voting',style=discord.ButtonStyle.primary,
                                 custom_id=f"election:{row['id']}:{uid}:open")
        button.callback=self.open
        self.add_item(button)

    def text(self):
        submitted=any(voter['user_id']==self.uid for voter in self.store.receipts(self.row['id']))
        return (ballot_introduction(self.row)+'\n\n'
                +('✅ You have submitted a ballot. You may change it before closing.\n\n' if submitted else
                  'Press **Start / continue voting** below to choose your nominees.\n\n')
                +'**Press Submit ballot when you are satisfied.**')

    async def interaction_check(self,interaction):
        if interaction.user.id!=self.uid:
            await interaction.response.send_message('This is someone else’s ballot.',ephemeral=True)
            return False
        return True

    async def open(self,interaction):
        await interaction.response.defer()
        try:
            row=self.store.get(self.row['id'])
            open_for(row,self.uid,datetime.now(timezone.utc).timestamp())
            view=BallotView(row,self.uid,self.store)
            await view.update_message(interaction)
            self.stop()
        except ValueError as error:
            await interaction.followup.send(str(error),ephemeral=True)

    async def on_error(self,interaction,error,item):
        await BallotView.on_error(self,interaction,error,item)


class BallotView(discord.ui.View):
    def __init__(self,row,uid,store):
        super().__init__(timeout=None)
        self.row=row
        self.uid=uid
        self.store=store
        self.ranking=[]
        self.page=0
        self.refresh()

    def text(self):
        lines=[ballot_introduction(self.row), '', '**Your choices so far:**']
        lines.extend(f'{index}. {name(self.row,uid)}' for index,uid in enumerate(self.ranking[:10],1))
        if len(self.ranking)>10:
            lines.append(f'…and {len(self.ranking)-10} more. Press **Review full ranking** to see every choice.')
        remaining=len(candidates(self.row))-len(self.ranking)
        if remaining>25:
            lines.append(f'Candidate page {self.page+1}/{(remaining+24)//25}; use the page buttons to browse.')
        if not self.ranking:
            lines.append('No choices yet. Select your first choice below.')
        lines += ['', '**Press Submit ballot when you are satisfied.**']
        return '\n'.join(lines)

    def draft_content(self):
        return self.text()+f"\n||DRAFT-V1:{self.row['id']}:{self.page}:"+','.join(map(str,self.ranking))+'||'

    async def update_message(self,interaction):
        content=self.draft_content()
        if len(content)<=1900:
            message=await interaction.edit_original_response(content=content,view=self,attachments=[])
        else:
            file=discord.File(io.BytesIO(content.encode('utf-8')),filename=f"draft-{self.row['id']}.txt")
            try:
                message=await interaction.edit_original_response(content=self.text(),view=self,attachments=[file])
            finally:
                file.close()
        track_menu(self.store,self.row,self.uid,message,'draft')

    async def interaction_check(self,interaction):
        if interaction.user.id!=self.uid:
            await interaction.response.send_message('This is someone else’s ballot.',ephemeral=True)
            return False
        try:
            open_for(self.store.get(self.row['id']),self.uid,datetime.now(timezone.utc).timestamp())
        except ValueError as error:
            await interaction.response.send_message(str(error),ephemeral=True)
            return False
        return True

    def refresh(self):
        self.clear_items()
        remaining=[candidate for candidate in self.row['config']['candidates'] if candidate['id'] not in self.ranking]
        self.page=min(self.page,max(0,(len(remaining)-1)//25))
        if remaining:
            select=discord.ui.Select(placeholder=f'Choose preference #{len(self.ranking)+1}',
                custom_id=f"election:{self.row['id']}:{self.uid}:pick",
                options=[discord.SelectOption(label=candidate['name'][:100],value=str(candidate['id']))
                         for candidate in remaining[self.page*25:(self.page+1)*25]])
            async def choose(interaction):
                await interaction.response.defer()
                uid=int(select.values[0])
                if uid not in self.ranking:
                    self.ranking.append(uid)
                self.page=0
                self.refresh()
                await self.update_message(interaction)
            select.callback=choose
            self.add_item(select)
        if len(remaining)>25:
            for delta,label in ((-1,'Previous candidates'),(1,'Next candidates')):
                button=discord.ui.Button(label=label,disabled=not 0<=self.page+delta<(len(remaining)+24)//25,
                    custom_id=f"election:{self.row['id']}:{self.uid}:page{delta}")
                async def move(interaction,delta=delta):
                    await interaction.response.defer()
                    self.page+=delta
                    self.refresh()
                    await self.update_message(interaction)
                button.callback=move
                self.add_item(button)
        undo=discord.ui.Button(label='Undo last choice',disabled=not self.ranking,
            custom_id=f"election:{self.row['id']}:{self.uid}:undo")
        async def undo_choice(interaction):
            await interaction.response.defer()
            if self.ranking:
                self.ranking.pop()
            self.page=0
            self.refresh()
            await self.update_message(interaction)
        undo.callback=undo_choice
        self.add_item(undo)
        review=discord.ui.Button(label='Review full ranking',disabled=not self.ranking,
            custom_id=f"election:{self.row['id']}:{self.uid}:review")
        async def review_ranking(interaction):
            await interaction.response.defer()
            await send_lines(interaction.channel,['**Your current draft ranking (not yet submitted):**']+
                             [f'{index}. {name(self.row,uid)}' for index,uid in enumerate(self.ranking,1)])
        review.callback=review_ranking
        self.add_item(review)
        submit=discord.ui.Button(label='Submit ballot',style=discord.ButtonStyle.success,disabled=len(self.ranking)<seat_count(self.row),
            custom_id=f"election:{self.row['id']}:{self.uid}:submit")
        submit.callback=self.submit
        self.add_item(submit)

    async def submit(self,interaction):
        await interaction.response.defer()
        try:
            async with lock:
                row=self.store.get(self.row['id'])
                open_for(row,self.uid,datetime.now(timezone.utc).timestamp())
                ranking=validate_ranking(self.ranking,candidates(row),seat_count(row))
                content=receipt_content(row,ranking)
                if len(content)<=1900:
                    receipt=await interaction.channel.send(content,allowed_mentions=discord.AllowedMentions.none())
                else:
                    file=discord.File(io.BytesIO(content.encode('utf-8')),filename=f"ballot-{row['id']}.txt")
                    try:
                        receipt=await interaction.channel.send('**Private ballot receipt attached.** '
                            'It counts only after Greg confirms submission.\n'+f"BALLOT-FILE-V1:{row['id']}",
                            file=file,allowed_mentions=discord.AllowedMentions.none())
                    finally:
                        file.close()
                when=datetime.now(timezone.utc).timestamp()
                open_for(row,self.uid,when)
                self.store.submit(row['id'],self.uid,interaction.channel.id,receipt.id,when)
                self.stop()
                entry=BallotEntryView(row,self.uid,self.store)
                entry.children[0].label='Change my vote'
                message=await interaction.edit_original_response(content=entry.text(),view=entry,attachments=[])
                track_menu(self.store,row,self.uid,message,'entry')
        except ValueError as error:
            await interaction.followup.send(str(error),ephemeral=True)

    async def on_error(self,interaction,error,item):
        # Never log interaction data or draft rankings.
        log.error('Election ballot interaction failed (%s)',type(error).__name__)
        if interaction.response.is_done():
            await interaction.followup.send('Your ballot could not be confirmed. Please retry or request a fresh ballot.',ephemeral=True)
        else:
            await interaction.response.send_message('Your ballot could not be confirmed. Please retry.',ephemeral=True)


async def open_ballot(context,key,*,store=None):
    store=store or ElectionStore()
    row=store.get(key)
    if context.guild.id!=row['config']['guild_id']:
        raise ValueError('Use this election’s server to request a ballot.')
    open_for(row,context.author.id,datetime.now(timezone.utc).timestamp())
    view=BallotEntryView(row,context.author.id,store)
    try:
        message=await context.author.send(view.text(),view=view,allowed_mentions=discord.AllowedMentions.none())
        track_menu(store,row,context.author.id,message,'entry')
    except discord.Forbidden:
        raise ValueError('Please allow DMs from Greg, then run the command again.') from None
    await context.message.add_reaction('✅')


async def close_election(client,key,*,store=None,now=None):
    store=store or ElectionStore()
    async with lock:
        row=store.get(key)
        if row['status']=='cancelled':
            raise ValueError('This election was cancelled.')
        if row['status']!='closed':
            row=store.freeze(key,now or datetime.now(timezone.utc).timestamp())
            ballots=[]
            for voter in store.receipts(key):
                if voter['user_id'] not in row['config']['voters'] or voter['submitted']>row['cutoff']:
                    raise ValueError('A receipt reference failed eligibility or cutoff checks; counting stopped.')
                channel=client.get_channel(voter['dm_id']) or await client.fetch_channel(voter['dm_id'])
                if channel.recipient.id!=voter['user_id']:
                    raise ValueError('A saved receipt belongs to a different DM; counting stopped.')
                message=await channel.fetch_message(voter['receipt_id'])
                ballots.append(await load_receipt(message,row,client.user.id))
            store.finish(key,count_stv(candidates(row),ballots,seats=seat_count(row)))
            row=store.get(key)
        if store.claim_delivery(key):
            try:
                channel=await client.fetch_channel(row['config']['channel_id'])
                posted=await post_result(channel,row)
            except (discord.Forbidden,discord.NotFound):
                store.delivery(key,'waiting')
                raise
            else:
                store.delivery(key,'sent',posted.id)
        return row


async def create(context,args,*,store=None,now=None):
    store=store or ElectionStore()
    args=list(args)
    seats=2
    if len(args)>1 and re.fullmatch(r'-?\d+',args[1]):
        seats=int(args.pop(1))
    if seats<1:
        raise ValueError('The number of winning seats must be positive.')
    if len(args)<5:
        raise ValueError('Use $election create "Election name" seats month/day/year hour:minute AM/PM @candidate-or-role ...')
    title=args[0]
    if not 1<=len(title)<=80:
        raise ValueError('Election names must be 1–80 characters.')
    try:
        deadline=datetime.strptime(' '.join(args[1:4]),'%m/%d/%Y %I:%M %p').replace(tzinfo=ST)
    except ValueError:
        raise ValueError('Use month/day/year hour:minute AM/PM for the closing date, in ST (UTC−4).') from None
    timestamp=(now or datetime.now(timezone.utc)).timestamp()
    if deadline.timestamp()<=timestamp:
        raise ValueError('The closing date must be in the future.')
    ids=[]
    member_map={member.id:member async for member in context.guild.fetch_members(limit=None)}
    for arg in args[4:]:
        role_match=re.fullmatch(r'<@&(\d+)>',arg)
        user_match=re.fullmatch(r'<@!?(\d+)>',arg)
        if role_match:
            role_id=int(role_match[1])
            if context.guild.get_role(role_id) is None:
                raise ValueError('A candidate role was not found in this server.')
            ids.extend(sorted(member.id for member in member_map.values()
                              if not member.bot and any(role.id==role_id for role in member.roles)))
        elif user_match:
            ids.append(int(user_match[1]))
        else:
            raise ValueError('List candidates as user or role mentions after the closing date.')
    ids=list(dict.fromkeys(ids))
    if len(ids)<seats:
        raise ValueError(f'The mentions expand to {len(ids)} distinct candidates, but {seats} winning seats require at least {seats} candidates.')
    choices=[]
    for uid in ids:
        member=member_map.get(uid) or await context.guild.fetch_member(uid)
        if member.bot:
            raise ValueError('Bots cannot stand as candidates.')
        choices.append(dict(id=uid,name=member.display_name))
    voters=[member.id for member in member_map.values()
            if not member.bot and any(role.id==COUNCIL_ROLE for role in member.roles)]
    if not voters:
        raise ValueError('No eligible Council voters were found; the election was not opened.')
    key=store.create(dict(title=title,deadline=deadline.timestamp(),guild_id=context.guild.id,
        channel_id=context.channel.id,creator_id=context.author.id,created_at=timestamp,
        candidates=choices,voters=sorted(set(voters)),seats=seats))
    for uid in voters:
        store.mark_repaired(key,uid)
    await send_lines(context.channel,election_summary(store.get(key),store).splitlines())
    await invite_voters(context.guild,store.get(key),store=store,members=member_map,now=timestamp)
    invitations=store.invitations(key)
    sent=sum(invitation['status']=='sent' for invitation in invitations.values())
    failed=[uid for uid,invitation in invitations.items() if invitation['status'] in ('blocked','failed')]
    await send_lines(context.channel,[f'**Election #{key}: ballot DMs sent to {sent}/{len(voters)} Council voters.**',
        'DM delivery needs attention: '+(', '.join(f'<@{uid}>' for uid in failed) or 'Nobody'),
        'Voters with blocked DMs can enable them and use `$vote '+str(key)+'`. Unsubmitted ballots receive daily reminders.'])
    return key


async def invite_voters(guild,row,*,store=None,members=None,now=None,pause=0.25):
    store=store or ElectionStore()
    supplied_now=now
    now=datetime.now(timezone.utc).timestamp() if now is None else now
    if row['status']!='open' or now>=row['config']['deadline']:
        return
    submitted={voter['user_id'] for voter in store.receipts(row['id'])}
    for uid in row['config']['voters']:
        if uid in submitted:
            continue
        # Serializes each send against submission/closing. Recheck inside the
        # lock so someone who just voted does not receive a stale reminder.
        async with lock:
            current=store.get(row['id'])
            check_time=supplied_now if supplied_now is not None else datetime.now(timezone.utc).timestamp()
            if current['status']!='open' or check_time>=current['config']['deadline']:
                return
            if any(voter['user_id']==uid for voter in store.receipts(row['id'])):
                continue
            previous=store.invitations(row['id']).get(uid)
            if not store.claim_invitation(row['id'],uid,check_time):
                continue
            view=BallotEntryView(current,uid,store)
            try:
                member=(members or {}).get(uid) or await guild.fetch_member(uid)
                content=view.text()
                if previous:
                    content+='\n\n**Voting reminder:** We haven’t received your submitted ballot yet.'
                message=await member.send(content,view=view,allowed_mentions=discord.AllowedMentions.none())
                track_menu(store,current,uid,message,'entry')
            except (discord.Forbidden,discord.NotFound):
                view.stop()
                store.invitation_status(row['id'],uid,'blocked')
            except discord.HTTPException:
                view.stop()
                store.invitation_status(row['id'],uid,'failed')
                log.warning('Election #%s voter invitation could not be delivered',row['id'])
            else:
                store.invitation_status(row['id'],uid,'sent')
        await asyncio.sleep(pause)


async def control(context,client,*,store=None):
    store=store or ElectionStore()
    if context.guild.id!=GUILD_ID:
        raise ValueError('Council elections are available in FF.')
    args=context.args
    if not args or args[0].lower()=='help':
        await context.send(HELP)
        return
    action=args[0].lower()
    if action=='create':
        await create(context,args[1:],store=store)
        return
    if action=='list' and len(args)==1:
        rows=store.all()
        await send_lines(context.channel,[f"**#{row['id']} {safe(row['config']['title'])}** — {row['status']}" for row in rows] or ['No elections yet.'])
        return
    if len(args)!=2 or not args[1].isdigit() or action not in ('status','close','results','rounds','cancel'):
        raise ValueError(HELP)
    key=int(args[1])
    row=store.get(key)
    if action=='close':
        await context.send('Closing the election and reading private ballot receipts. This may take a moment.')
        await close_election(client,key,store=store)
        await context.send(f'Election #{key} counted. Use `$election results {key}` to view the result.')
    elif action=='cancel':
        async with lock:
            if store.get(key)['status']!='open':
                raise ValueError('Only an open election can be cancelled.')
            store.cancel(key)
        await context.send(f'Election #{key} cancelled. Its ballots will not be counted.')
    elif action=='rounds':
        await send_lines(context.channel,round_text(row))
    else:
        await send_lines(context.channel,(results_text(row) if action=='results' else election_summary(row,store)).splitlines())


async def close_due(client,*,store=None):
    store=store or ElectionStore()
    now=datetime.now(timezone.utc).timestamp()
    for row in store.all(limit=None):
        if row['status']=='open' and row['config']['deadline']>now:
            from commands.election_recovery import restore
            try:
                await restore(client,row,store)
            except Exception as error:
                log.error('Election #%s menu restoration failed (%s)',row['id'],type(error).__name__)
        if (row['status']=='open' and row['config']['deadline']<=now) or row['status']=='counting' or (row['status']=='closed' and row['delivery']=='waiting'):
            try:
                await close_election(client,row['id'],store=store)
            except Exception as error:
                log.error('Election #%s could not close (%s); receipt references retained for retry',row['id'],type(error).__name__)
        elif row['status']=='open':
            guild=client.get_guild(row['config']['guild_id'])
            if guild is not None:
                try:
                    await invite_voters(guild,row,store=store)
                except Exception as error:
                    log.error('Election #%s reminder pass failed (%s)',row['id'],type(error).__name__)
