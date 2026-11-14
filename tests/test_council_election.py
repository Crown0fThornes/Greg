from datetime import datetime, timezone
import json
import itertools
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, patch

import discord

from commands import council_election as election
from commands.election_store import ElectionStore


message_ids=itertools.count(10000)

def menu_message():
    return NS(id=next(message_ids),channel=NS(id=1000))

def dm_send():
    return AsyncMock(side_effect=lambda *args,**kwargs:menu_message())


def config(**overrides):
    result=dict(title='Council seats',deadline=4102444800,guild_id=election.GUILD_ID,
                channel_id=999,creator_id=10,created_at=1,
                candidates=[dict(id=uid,name=f'Candidate {uid}') for uid in (1,2,3)],voters=[10,11,12])
    result.update(overrides)
    return result


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=ElectionStore(Path(self.tmp.name)/'elections.sqlite3')
        self.key=self.store.create(config())

    def test_replacing_ballot_stores_only_one_reference_not_rankings(self):
        self.store.submit(self.key,10,100,101,5)
        self.store.submit(self.key,10,100,102,6)
        self.assertEqual(len(self.store.receipts(self.key)),1)
        self.assertEqual(self.store.receipts(self.key)[0]['receipt_id'],102)
        with self.store.connect() as db:
            self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(voter)')],
                             ['election_id','user_id','dm_id','receipt_id','submitted'])

    def test_freeze_prevents_cutoff_moving_on_retry(self):
        self.assertEqual(self.store.freeze(self.key,100)['cutoff'],100)
        self.assertEqual(self.store.freeze(self.key,200)['cutoff'],100)

    def test_eligibility_and_deadline(self):
        row=self.store.get(self.key)
        election.open_for(row,10,100)
        for uid,when in ((99,100),(10,row['config']['deadline'])):
            with self.assertRaises(ValueError):
                election.open_for(row,uid,when)
        self.store.cancel(self.key)
        with self.assertRaises(ValueError):
            election.open_for(self.store.get(self.key),10,100)

    def test_receipt_validates_bot_author_and_election(self):
        row=self.store.get(self.key)
        content=election.receipt_content(row,[2,1])
        self.assertEqual(election.read_receipt(NS(author=NS(id=99),content=content),row,99),[2,1])
        for author,text in ((10,content),(99,content.replace('BALLOT-V1:1:','BALLOT-V1:2:'))):
            with self.assertRaises(ValueError):
                election.read_receipt(NS(author=NS(id=author),content=text),row,99)


class ElectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=ElectionStore(Path(self.tmp.name)/'elections.sqlite3')
        self.key=self.store.create(config())

    def client(self,ballots):
        row=self.store.get(self.key)
        channels={}
        for uid,ranking in ballots.items():
            receipt=NS(id=uid+100,author=NS(id=99),content=election.receipt_content(row,ranking))
            channels[uid+1000]=NS(recipient=NS(id=uid),fetch_message=AsyncMock(return_value=receipt))
            self.store.submit(self.key,uid,uid+1000,receipt.id,5)
        target=NS(send=AsyncMock(return_value=NS(id=9999)))
        client=NS(user=NS(id=99),get_channel=lambda key:channels.get(key),fetch_channel=AsyncMock(return_value=target))
        return client,target,channels

    async def test_close_uses_receipts_then_persists_only_aggregate_results_and_posts_once(self):
        client,target,channels=self.client({10:[1,2],11:[1,2],12:[3,2]})
        row=await election.close_election(client,self.key,store=self.store,now=100)
        self.assertEqual(row['status'],'closed')
        self.assertEqual(row['result']['ballots'],3)
        await election.close_election(client,self.key,store=self.store,now=200)
        target.send.assert_awaited_once()
        self.assertFalse(target.send.call_args.kwargs['allowed_mentions'].everyone)
        with self.store.connect() as db:
            result=json.loads(db.execute('SELECT result FROM election').fetchone()[0])
        self.assertNotIn('rankings',result)
        self.assertNotIn('voters',result)
        self.assertEqual(result['winners'],[1,3])
        self.assertEqual(result['tied'],[])
        self.assertIn('Elected: Candidate 3',target.send.call_args.args[0])

    async def test_final_tie_is_published_without_filling_second_seat(self):
        key=self.store.create(config(voters=list(range(10,24))))
        self.key=key
        rankings=[[1,2,3]]*4+[[1,3,2]]*4+[[2,3]]*3+[[3,2]]*3
        client,target,_=self.client(dict(zip(range(10,24),rankings)))
        row=await election.close_election(client,key,store=self.store,now=100)
        self.assertEqual(row['result']['winners'],[1])
        self.assertEqual(row['result']['tied'],[2,3])
        self.assertIn('Senior Member vote required',target.send.call_args.args[0])

    async def test_unreadable_receipt_stops_count_without_excluding_vote(self):
        client,target,channels=self.client({10:[1,2]})
        channels[1010].fetch_message.side_effect=RuntimeError('fetch interrupted')
        with self.assertRaises(RuntimeError):
            await election.close_election(client,self.key,store=self.store,now=100)
        self.assertEqual(self.store.get(self.key)['status'],'counting')
        self.assertIsNone(self.store.get(self.key)['result'])
        target.send.assert_not_awaited()
        channels[1010].fetch_message.side_effect=None
        await election.close_election(client,self.key,store=self.store,now=200)
        self.assertEqual(self.store.get(self.key)['cutoff'],100)

    async def test_wrong_dm_recipient_is_rejected(self):
        client,target,channels=self.client({10:[1,2]})
        channels[1010].recipient.id=11
        with self.assertRaises(ValueError):
            await election.close_election(client,self.key,store=self.store,now=100)
        self.assertIsNone(self.store.get(self.key)['result'])

    async def test_view_requires_two_choices_and_submits_private_receipt(self):
        view=election.BallotView(self.store.get(self.key),10,self.store)
        self.assertTrue(next(child for child in view.children if getattr(child,'label','')=='Submit ballot').disabled)
        view.ranking=[3,1]
        view.refresh()
        self.assertFalse(next(child for child in view.children if getattr(child,'label','')=='Submit ballot').disabled)
        interaction=NS(user=NS(id=10),response=NS(defer=AsyncMock()),
                       channel=NS(id=1000,send=AsyncMock(return_value=NS(id=100))),
                       edit_original_response=AsyncMock(return_value=menu_message()),followup=NS(send=dm_send()))
        await view.submit(interaction)
        self.assertEqual(self.store.receipts(self.key)[0]['receipt_id'],100)
        self.assertIn('3,1',interaction.channel.send.call_args.args[0])
        self.assertIsInstance(interaction.edit_original_response.call_args.kwargs['view'],election.BallotEntryView)
        self.assertTrue(view.is_finished())

    async def test_expired_view_cannot_submit(self):
        key=self.store.create(config(deadline=1))
        view=election.BallotView(self.store.get(key),10,self.store)
        view.ranking=[1,2]
        interaction=NS(response=NS(defer=AsyncMock()),channel=NS(send=dm_send()),followup=NS(send=dm_send()))
        await view.submit(interaction)
        interaction.channel.send.assert_not_awaited()
        self.assertEqual(self.store.receipts(key),[])
        self.assertIn('no longer',interaction.followup.send.call_args.args[0])
        view.stop()

    async def test_open_ballot_sends_only_dm_and_success_reaction(self):
        author=NS(id=10,send=dm_send())
        context=NS(guild=NS(id=election.GUILD_ID),author=author,message=NS(add_reaction=AsyncMock()))
        await election.open_ballot(context,self.key,store=self.store)
        self.assertTrue(author.send.call_args.args[0].startswith('# Council seats\n'))
        self.assertIsInstance(author.send.call_args.kwargs['view'],election.BallotEntryView)
        context.message.add_reaction.assert_awaited_once_with('✅')
        author.send.call_args.kwargs['view'].stop()

    async def test_create_freezes_current_council_and_date_uses_fixed_st(self):
        voter=NS(id=10,bot=False,roles=[NS(id=election.COUNCIL_ROLE)],send=dm_send())
        async def members(**kwargs):
            yield voter
            yield NS(id=11,bot=False,roles=[])
            yield NS(id=12,bot=True,roles=[NS(id=election.COUNCIL_ROLE)])
        guild=NS(id=election.GUILD_ID,fetch_members=members,
                 fetch_member=AsyncMock(side_effect=lambda uid:NS(id=uid,display_name=f'Name {uid}',bot=False)))
        context=NS(guild=guild,author=NS(id=10),channel=NS(id=999,send=dm_send()))
        key=await election.create(context,['November election','11/20/2026','8:00','PM','<@1>','<@2>','<@3>'],
                                  store=self.store,now=datetime(2026,11,11,tzinfo=timezone.utc))
        row=self.store.get(key)
        self.assertEqual(row['config']['voters'],[10])
        self.assertEqual(datetime.fromtimestamp(row['config']['deadline'],timezone.utc).isoformat(),'2026-11-21T00:00:00+00:00')
        self.assertEqual(row['config']['channel_id'],999)
        voter.send.assert_awaited_once()
        self.assertTrue(voter.send.call_args.args[0].startswith('# November election\n'))
        voter.send.call_args.kwargs['view'].stop()

    async def test_role_candidates_expand_deduplicate_and_exclude_bots(self):
        people=[NS(id=uid,display_name=f'Candidate {uid}',bot=uid==4,
                   roles=[NS(id=200)],send=dm_send()) for uid in (1,2,3,4)]
        voter=NS(id=10,bot=False,roles=[NS(id=election.COUNCIL_ROLE)],send=dm_send())
        async def members(**kwargs):
            for person in people+[voter]:
                yield person
        guild=NS(id=election.GUILD_ID,fetch_members=members,get_role=lambda rid:NS(id=rid))
        context=NS(guild=guild,author=NS(id=10),channel=NS(id=999,send=dm_send()))
        key=await election.create(context,['Election','11/20/2026','8:00','PM','<@&200>','<@1>'],
                                  store=self.store,now=datetime(2026,11,11,tzinfo=timezone.utc))
        self.assertEqual(election.candidates(self.store.get(key)),[1,2,3])
        voter.send.assert_awaited_once()
        voter.send.call_args.kwargs['view'].stop()

    async def test_create_role_with_nine_candidates_and_three_seats(self):
        people=[NS(id=uid,display_name=f'Candidate {uid}',bot=False,
                   roles=[NS(id=200)],send=dm_send()) for uid in range(1,10)]
        voter=NS(id=10,bot=False,roles=[NS(id=election.COUNCIL_ROLE)],send=dm_send())
        async def members(**kwargs):
            for person in people+[voter]:
                yield person
        guild=NS(id=election.GUILD_ID,fetch_members=members,get_role=lambda rid:NS(id=rid))
        context=NS(guild=guild,author=NS(id=10),channel=NS(id=999,send=dm_send()))
        key=await election.create(context,['Election','3','11/20/2026','8:00','PM','<@&200>'],
                                  store=self.store,now=datetime(2026,11,11,tzinfo=timezone.utc))
        row=self.store.get(key)
        self.assertEqual(election.candidates(row),list(range(1,10)))
        self.assertEqual(row['config']['seats'],3)
        voter.send.call_args.kwargs['view'].stop()
        view=election.BallotView(row,10,self.store)
        view.ranking=[1,2]
        view.refresh()
        self.assertTrue(next(child for child in view.children if getattr(child,'label','')=='Submit ballot').disabled)
        view.ranking=[1,2,3]
        view.refresh()
        self.assertFalse(next(child for child in view.children if getattr(child,'label','')=='Submit ballot').disabled)
        view.stop()

    async def test_large_candidate_lists_have_pages_and_bounded_preview(self):
        key=self.store.create(config(seats=3,candidates=[dict(id=uid,name='Candidate '+str(uid)) for uid in range(1,61)]))
        view=election.BallotView(self.store.get(key),10,self.store)
        select=next(child for child in view.children if isinstance(child,discord.ui.Select))
        self.assertEqual(len(select.options),25)
        self.assertEqual(select.options[0].value,'1')
        view.page=2
        view.refresh()
        select=next(child for child in view.children if isinstance(child,discord.ui.Select))
        self.assertEqual([option.value for option in select.options],list(map(str,range(51,61))))
        view.ranking=list(range(1,61))
        view.refresh()
        self.assertLess(len(view.text()),1900)
        self.assertIn('50 more',view.text())
        view.stop()

    async def test_long_receipts_are_read_from_private_attachment(self):
        row=self.store.get(self.key)
        text=election.receipt_content(row,[3,1])
        attachment=NS(filename=f'ballot-{self.key}.txt',read=AsyncMock(return_value=text.encode('utf-8')))
        message=NS(author=NS(id=99),content=f'BALLOT-FILE-V1:{self.key}',attachments=[attachment])
        self.assertEqual(await election.load_receipt(message,row,99),[3,1])

    async def test_reminders_are_daily_and_stop_after_submission(self):
        people={uid:NS(id=uid,send=dm_send()) for uid in (10,11,12)}
        guild=NS(fetch_member=AsyncMock(side_effect=lambda uid:people[uid]))
        row=self.store.get(self.key)
        await election.invite_voters(guild,row,store=self.store,now=100,pause=0)
        await election.invite_voters(guild,row,store=self.store,now=200,pause=0)
        self.assertEqual([person.send.await_count for person in people.values()],[1,1,1])
        self.store.submit(self.key,10,1000,1001,300)
        await election.invite_voters(guild,row,store=self.store,now=86500,pause=0)
        self.assertEqual([person.send.await_count for person in people.values()],[1,2,2])
        self.assertIn('Voting reminder',people[11].send.call_args.args[0])
        self.store.cancel(self.key)
        await election.invite_voters(guild,self.store.get(self.key),store=self.store,now=172900,pause=0)
        self.assertEqual(people[11].send.await_count,2)
        for person in people.values():
            for call in person.send.call_args_list:
                call.kwargs['view'].stop()

    async def test_blocked_dm_does_not_prevent_other_voters_receiving_ballots(self):
        blocked=NS(id=10,send=AsyncMock(side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'blocked')))
        delivered=NS(id=11,send=dm_send())
        third=NS(id=12,send=dm_send())
        people={10:blocked,11:delivered,12:third}
        guild=NS(fetch_member=AsyncMock(side_effect=lambda uid:people[uid]))
        await election.invite_voters(guild,self.store.get(self.key),store=self.store,now=100,pause=0)
        self.assertEqual(self.store.invitations(self.key)[10]['status'],'blocked')
        delivered.send.assert_awaited_once()
        self.assertIn('<@10>',election.election_summary(self.store.get(self.key),self.store))
        for person in (delivered,third):
            person.send.call_args.kwargs['view'].stop()
