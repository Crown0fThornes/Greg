"""Private DM ballots for Council elections, without changing core dispatch."""
import asyncio
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import logging
import re

import discord

from commands.election_count import count_stv, validate_ranking
from commands.election_store import ElectionStore

GUILD_ID=647883751853916162
COUNCIL_ROLE=648188387836166168
ST=timezone(timedelta(hours=-4))
lock=asyncio.Lock()
log=logging.getLogger(__name__)
HELP='''**Council elections**
`$election create "Election name" month/day/year hour:minute AM/PM @candidate-or-role ...`
Opens a two-seat election with 2–7 candidates. Times use ST (UTC−4).
Role mentions add their non-bot members as candidates (2–7 distinct candidates total).
Current Council members receive DM ballots immediately and reminders every 24 hours until submitted.
`$vote ID` — receive a private ballot; submit again to replace your vote before closing.
`$election list` / `$election status ID` — elections and turnout, without interim tallies.
`$election close ID` — close early and count; normally closes automatically at its deadline.
`$election results ID` / `$election rounds ID` — aggregate results and count rounds.
`$election cancel ID` — cancel an open election.
Tied seats remain unfilled for a Senior Member vote. No random tie-breaks.'''


def safe(text):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text.replace('\n',' ')[:100]))


def candidates(row):
    return [candidate['id'] for candidate in row['config']['candidates']]


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
    lines += ['', 'Your latest submitted receipt is your vote. Use the server command '
              f"`$vote {row['id']}` to replace it before closing.",
              'This receipt counts only after Greg confirms that your ballot was submitted.',
              f"BALLOT-V1:{row['id']}:"+','.join(map(str,ranking))]
    return '\n'.join(lines)


def read_receipt(message,row,bot_id):
    if message.author.id!=bot_id:
        raise ValueError('A saved ballot receipt was not authored by Greg; counting stopped.')
    match=re.search(rf"^BALLOT-V1:{row['id']}:(\d+(?:,\d+)*)$",message.content,re.M)
    if not match:
        raise ValueError('A saved ballot receipt is unreadable; counting stopped.')
    return validate_ranking([int(uid) for uid in match[1].split(',')],candidates(row))


def election_summary(row,store):
    config=row['config']
    submitted={voter['user_id'] for voter in store.receipts(row['id'])}
    missing=[uid for uid in config['voters'] if uid not in submitted]
    invitations=store.invitations(row['id'])
    blocked=[uid for uid in missing if invitations.get(uid,{}).get('status') in ('blocked','failed')]
    return (f"**Election #{row['id']}: {safe(config['title'])} — {row['status']}**\n"
            f"Two seats · {len(config['candidates'])} candidates · {len(config['voters'])} eligible Council voters\n"
            f"Ballots submitted: {len(submitted)}\n"
            'Awaiting ballots: '+(', '.join(f'<@{uid}>' for uid in missing) or 'Nobody')+'\n'
            +('DM delivery needs attention: '+', '.join(f'<@{uid}>' for uid in blocked)+'\n' if blocked else '')+
            f"Closes: <t:{int(config['deadline'])}:F>\n"
            'Candidates: '+', '.join(name(row,uid) for uid in candidates(row))+'\n'
            f"Council voters receive DM ballots automatically. Use `$vote {row['id']}` for a fresh ballot.\n"
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
           f"Valid ballots: {result['ballots']} · Seats: 2 · Quota: {result['quota']}"]
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
        lines.append('No ballots were submitted. Neither seat was filled.')
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


async def send_lines(channel,lines):
    page=''
    for line in lines:
        if len(page)+len(line)+1>1900:
            await channel.send(page,allowed_mentions=discord.AllowedMentions.none())
            page=''
        page+=line+'\n'
    if page:
        await channel.send(page,allowed_mentions=discord.AllowedMentions.none())


class BallotView(discord.ui.View):
    def __init__(self,row,uid,store):
        super().__init__(timeout=600)
        self.row=row
        self.uid=uid
        self.store=store
        self.ranking=[]
        self.refresh()

    def text(self):
        lines=[f"**Private ballot — Election #{self.row['id']}: {safe(self.row['config']['title'])}**",
               'Choose candidates in preference order: first choice first. Rank at least 2; '
               'you may rank every candidate you would accept. Unranked candidates receive no further transfers.',
               '', '**Your draft ranking:**']
        lines.extend(f'{index}. {name(self.row,uid)}' for index,uid in enumerate(self.ranking,1))
        if not self.ranking:
            lines.append('No choices yet. Select your first choice below.')
        lines += ['', 'Press **Submit ballot** to save this ranking. A draft is not a vote. '
                  'You can replace your submitted ballot until closing. This menu expires after 10 minutes; '
                  f"run `$vote {self.row['id']}` in the server for a fresh menu."]
        return '\n'.join(lines)

    async def interaction_check(self,interaction):
        if interaction.user.id!=self.uid:
            await interaction.response.send_message('This is someone else’s ballot.',ephemeral=True)
            return False
        return True

    def refresh(self):
        self.clear_items()
        remaining=[candidate for candidate in self.row['config']['candidates'] if candidate['id'] not in self.ranking]
        if remaining:
            select=discord.ui.Select(placeholder=f'Choose preference #{len(self.ranking)+1}',
                options=[discord.SelectOption(label=candidate['name'][:100],value=str(candidate['id'])) for candidate in remaining])
            async def choose(interaction):
                uid=int(select.values[0])
                if uid not in self.ranking:
                    self.ranking.append(uid)
                self.refresh()
                await interaction.response.edit_message(content=self.text(),view=self)
            select.callback=choose
            self.add_item(select)
        undo=discord.ui.Button(label='Undo last choice',disabled=not self.ranking)
        async def undo_choice(interaction):
            if self.ranking:
                self.ranking.pop()
            self.refresh()
            await interaction.response.edit_message(content=self.text(),view=self)
        undo.callback=undo_choice
        self.add_item(undo)
        submit=discord.ui.Button(label='Submit ballot',style=discord.ButtonStyle.success,disabled=len(self.ranking)<2)
        submit.callback=self.submit
        self.add_item(submit)

    async def submit(self,interaction):
        await interaction.response.defer()
        try:
            async with lock:
                row=self.store.get(self.row['id'])
                open_for(row,self.uid,datetime.now(timezone.utc).timestamp())
                ranking=validate_ranking(self.ranking,candidates(row))
                receipt=await interaction.channel.send(receipt_content(row,ranking),allowed_mentions=discord.AllowedMentions.none())
                when=datetime.now(timezone.utc).timestamp()
                open_for(row,self.uid,when)
                self.store.submit(row['id'],self.uid,interaction.channel.id,receipt.id,when)
                self.stop()
                await interaction.edit_original_response(content='✅ Your ballot was submitted. Your latest submitted ballot counts.',view=None)
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
    view=BallotView(row,context.author.id,store)
    try:
        await context.author.send(view.text(),view=view,allowed_mentions=discord.AllowedMentions.none())
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
                ballots.append(read_receipt(message,row,client.user.id))
            store.finish(key,count_stv(candidates(row),ballots))
            row=store.get(key)
        if store.claim_delivery(key):
            try:
                channel=await client.fetch_channel(row['config']['channel_id'])
                posted=await channel.send(results_text(row),allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden,discord.NotFound):
                store.delivery(key,'waiting')
                raise
            else:
                store.delivery(key,'sent',posted.id)
        return row


async def create(context,args,*,store=None,now=None):
    store=store or ElectionStore()
    if len(args)<5:
        raise ValueError('Use $election create "Election name" month/day/year hour:minute AM/PM @candidate-or-role ...')
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
    if not 2<=len(ids)<=7:
        raise ValueError(f'The mentions expand to {len(ids)} distinct candidates. Choose 2–7 for the two seats.')
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
        candidates=choices,voters=sorted(set(voters))))
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
            view=BallotView(current,uid,store)
            try:
                member=(members or {}).get(uid) or await guild.fetch_member(uid)
                prefix='**Voting reminder: your ballot has not been submitted yet.**\n\n' if previous else '**Council voting is open!**\n\n'
                await member.send(prefix+view.text(),view=view,allowed_mentions=discord.AllowedMentions.none())
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
