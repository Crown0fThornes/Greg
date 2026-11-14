from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, Mock

from commands import council_election as election
from commands.election_recovery import draft_view, restore
from commands.election_store import ElectionStore


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=ElectionStore(Path(self.tmp.name)/'elections.sqlite3')
        self.key=self.store.create(dict(title='Council',deadline=4102444800,guild_id=election.GUILD_ID,
            channel_id=999,creator_id=10,created_at=1,seats=2,
            candidates=[dict(id=uid,name=f'Candidate {uid}') for uid in range(1,40)],voters=[10]))
        self.row=self.store.get(self.key)

    async def test_views_are_persistent_and_have_stable_custom_ids(self):
        for cls in (election.BallotEntryView,election.BallotView):
            view=cls(self.row,10,self.store)
            again=cls(self.row,10,self.store)
            self.assertTrue(view.is_persistent())
            self.assertIsNone(view.timeout)
            self.assertEqual([item.custom_id for item in view.children],
                             [item.custom_id for item in again.children])
            self.assertNotIn('$vote',view.text())
            self.assertTrue(view.text().startswith('# Council\n'))
            self.assertIn('First pick = your top choice',view.text())
            self.assertIn('**2 positions.**',view.text())
            self.assertIn('**You must rank at least 2 nominees',view.text())
            self.assertIn('Ranking more nominees does not dilute',view.text())
            self.assertIn('please contact Lincoln',view.text())
            self.assertIn('**Press submit ballot when you are satisfied.**',view.text())
            view.stop()
            again.stop()

    async def test_open_button_acknowledges_and_starts_ballot_in_same_dm(self):
        entry=election.BallotEntryView(self.row,10,self.store)
        message=NS(id=100,channel=NS(id=1000))
        interaction=NS(response=NS(defer=AsyncMock()),
                       edit_original_response=AsyncMock(return_value=message),followup=NS(send=AsyncMock()))
        await entry.open(interaction)
        interaction.response.defer.assert_awaited_once()
        view=interaction.edit_original_response.call_args.kwargs['view']
        self.assertIsInstance(view,election.BallotView)
        self.assertTrue(entry.is_finished())
        self.assertEqual(self.store.menus(self.key)[0]['kind'],'draft')
        self.assertIn('DRAFT-V1',interaction.edit_original_response.call_args.kwargs['content'])
        view.stop()

    async def test_draft_and_page_restore_from_dm_after_restart(self):
        view=election.BallotView(self.row,10,self.store)
        view.ranking=[3,1,7]
        view.page=1
        view.refresh()
        message=NS(id=100,channel=NS(id=1000),author=NS(id=99),content=view.draft_content(),attachments=[])
        self.store.menu(self.key,10,1000,100,'draft')
        self.store.mark_repaired(self.key,10)
        client=NS(user=NS(id=99),get_channel=lambda cid:NS(recipient=NS(id=10),fetch_message=AsyncMock(return_value=message)),
                  get_guild=lambda gid:None,add_view=Mock())
        await restore(client,self.row,self.store)
        recovered=client.add_view.call_args.args[0]
        self.assertEqual(recovered.ranking,[3,1,7])
        self.assertEqual(recovered.page,1)
        self.assertTrue(recovered.is_persistent())
        self.assertEqual(client.add_view.call_args.kwargs['message_id'],100)
        await restore(client,self.row,self.store)
        client.add_view.assert_called_once()
        with self.store.connect() as db:
            columns=[row[1] for row in db.execute('PRAGMA table_info(ballot_menu)')]
            self.assertEqual(columns,['message_id','election_id','user_id','dm_id','kind'])
        view.stop()
        recovered.stop()

    async def test_repair_replaces_old_dead_menu_and_preserves_submitted_ballot(self):
        self.store.submit(self.key,10,1000,1234,100)
        channel=NS(id=1000)
        old=NS(id=200,channel=channel,author=NS(id=99),
               content=f'**Private ballot — Election #{self.key}: Council**\nOld expired menu',
               attachments=[],edit=AsyncMock())
        unrelated=NS(id=201,channel=channel,author=NS(id=99),content='Unrelated DM',attachments=[],edit=AsyncMock())
        async def history(**kwargs):
            for message in (old,unrelated):
                yield message
        channel.history=history
        guild=NS(fetch_member=AsyncMock(return_value=NS(create_dm=AsyncMock(return_value=channel))))
        client=NS(user=NS(id=99),get_guild=lambda gid:guild,add_view=Mock())
        await restore(client,self.row,self.store)
        old.edit.assert_awaited_once()
        view=old.edit.call_args.kwargs['view']
        self.assertIsInstance(view,election.BallotEntryView)
        self.assertIn('You have submitted',old.edit.call_args.kwargs['content'])
        unrelated.edit.assert_not_awaited()
        self.assertEqual(self.store.receipts(self.key)[0]['receipt_id'],1234)
        self.assertTrue(self.store.repaired(self.key,10))
        await restore(client,self.row,self.store)
        old.edit.assert_awaited_once()
        view.stop()

    async def test_long_draft_restores_from_dm_attachment(self):
        view=election.BallotView(self.row,10,self.store)
        view.ranking=list(range(1,35))
        attachment=NS(filename=f'draft-{self.key}.txt',read=AsyncMock(return_value=view.draft_content().encode()))
        recovered=await draft_view(self.row,10,self.store,NS(content='',attachments=[attachment]))
        self.assertEqual(recovered.ranking,list(range(1,35)))
        view.stop()
        recovered.stop()

    async def test_owner_and_deadline_checks_on_persistent_menu(self):
        view=election.BallotView(self.row,10,self.store)
        interaction=NS(user=NS(id=11),response=NS(send_message=AsyncMock()))
        self.assertFalse(await view.interaction_check(interaction))
        interaction.user.id=10
        self.store.cancel(self.key)
        self.assertFalse(await view.interaction_check(interaction))
        self.assertIn('no longer accepting',interaction.response.send_message.call_args.args[0])
        view.stop()
