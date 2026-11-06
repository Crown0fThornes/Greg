import asyncio
from datetime import datetime,timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock,patch

from commands import rolodex_import_job as background
from persistence.import_membership_history import JOINLIST,LEAVELIST
from persistence.sqlite_db import connect
from persistence.rolodex import FF_GUILD,Rolodex


class BackgroundTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store=Rolodex(Path(tmp.name)/'import.sqlite3')
        self.history_calls=[]
        def channel(cid):
            async def history(**kwargs):
                self.history_calls.append((cid,kwargs.get('after')))
                after=getattr(kwargs.get('after'),'id',0)
                for mid in [cid+1,cid+2]:
                    if mid>after:
                        yield NS(id=mid,guild=NS(id=FF_GUILD),channel=NS(id=cid),
                                 author=NS(id=999),content='[P] Lincoln has joined ffc',
                                 created_at=datetime(2026,10,25,tzinfo=timezone.utc))
            return NS(history=history)
        self.context=NS(guild=NS(id=FF_GUILD,members=[],fetch_channel=AsyncMock(side_effect=lambda cid:channel(cid))))

    def job(self):
        return dict(message=NS(edit=AsyncMock()),counts=dict(messages=0,resolved=0,unresolved=0,unparsed_lines=0),
                    updated=-100000000,bot_id=999,status='running')

    async def test_paced_import_progress_checkpoints_and_resume(self):
        job=self.job()
        await background.run(self.context,self.store,job,pause=0)
        self.assertEqual(job['status'],'complete')
        self.assertEqual(job['counts']['messages'],4)
        self.assertGreaterEqual(job['message'].edit.await_count,2)
        with connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rolodex_import_cursor').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM historical_identity').fetchone()[0],1)
        again=self.job()
        await background.run(self.context,self.store,again,pause=0)
        self.assertEqual(again['counts']['messages'],0)
        self.assertTrue(all(after is not None for _,after in self.history_calls[-2:]))
        full=self.job()
        await background.run(self.context,self.store,full,full=True,pause=0)
        self.assertEqual(full['counts']['messages'],4)
        with connect(self.store.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM membership_event').fetchone()[0],4)

    async def test_default_pacing_yields_between_each_message(self):
        job=self.job()
        with patch.object(background.asyncio,'sleep',new=AsyncMock()) as sleep:
            await background.run(self.context,self.store,job)
        self.assertEqual(sleep.await_count,4)
        self.assertTrue(all(call.args==(0.2,) for call in sleep.await_args_list))

    async def test_trial_caps_each_source_and_leaves_checkpoints_unchanged(self):
        calls=[]
        def channel(cid):
            async def history(**kwargs):
                calls.append(kwargs)
                # Deliberately exceed the requested limit to test the defensive cap.
                for index in range(40):
                    yield NS(id=cid+index+1,guild=NS(id=FF_GUILD),channel=NS(id=cid),
                             author=NS(id=999),content='[P] Lincoln has joined ffc',
                             created_at=datetime(2026,10,25,tzinfo=timezone.utc))
            return NS(history=history)
        self.context.guild.fetch_channel=AsyncMock(side_effect=channel)
        with connect(self.store.path) as db:
            db.execute('INSERT INTO rolodex_import_cursor VALUES (?,?)',(JOINLIST,777))
        job=self.job()
        await background.run(self.context,self.store,job,test=True,pause=0)
        self.assertEqual(job['counts']['messages'],50)
        self.assertTrue(job['status'].startswith('trial complete'))
        self.assertTrue(all(c['limit']==25 and c['oldest_first'] is False and 'after' not in c for c in calls))
        with connect(self.store.path) as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM rolodex_import_cursor')],[(JOINLIST,777)])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM membership_event').fetchone()[0],50)
