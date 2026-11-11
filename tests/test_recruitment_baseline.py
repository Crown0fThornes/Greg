from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock

from commands import recruitment_baseline as baseline
from commands import recruitment_review as review


class BaselineTests(unittest.TestCase):
    def test_window_imports_only_full_weeks_within_last_twelve_months(self):
        start,end = baseline.window(datetime(2026,11,11,12,tzinfo=timezone.utc))
        self.assertEqual(start.isoformat(),'2025-11-17T00:00:00-04:00')
        self.assertEqual(end.isoformat(),'2026-11-09T00:00:00-04:00')
        self.assertEqual((start.weekday(),end.weekday()),(0,0))
        # February 29 can be converted to the previous non-leap year.
        start,end = baseline.window(datetime(2028,2,29,12,tzinfo=timezone.utc))
        self.assertEqual(start.year,2027)
        self.assertEqual(start.weekday(),0)

    def test_weekly_report_counts_override_imported_duplicates_and_exclude_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            with review.connect(Path(tmp)/'review.sqlite3') as db:
                db.executemany('INSERT INTO baseline_week VALUES (?,?)',[
                    ('2026-10-19',json.dumps([1]*7)),
                    ('2026-10-26',json.dumps([2]*7)),
                    ('2026-11-02',json.dumps([99]*7))])
                db.execute("INSERT INTO week VALUES (?,?,?,'','sent',123)",
                           ('2026-10-26',json.dumps([3]*7),'{}'))
                self.assertEqual(review.prior_counts(db,'2026-11-02'),[[1]*7,[3]*7])


class ImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupted_scan_resumes_without_partial_baseline_or_double_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.sqlite3'
            state = baseline.new_state(datetime(2026,11,11,12,tzinfo=timezone.utc))
            baseline.save(path,state)
            start = datetime.fromisoformat(state['start'])
            messages = [NS(id=uid,created_at=start+timedelta(minutes=uid),author=NS(id=99),
                           content=f'**Welcome to Town, <@{uid}>!**') for uid in range(1,202)]
            broken = True
            cursors = []
            def history(**kwargs):
                cursor = getattr(kwargs['after'],'id',0)
                cursors.append(cursor)
                async def items():
                    if cursor==100 and broken:
                        raise RuntimeError('temporary Discord failure')
                    for message in [m for m in messages if m.id>cursor][:kwargs['limit']]:
                        yield message
                return items()
            guild = NS(fetch_channel=AsyncMock(return_value=NS(history=history)))
            with self.assertRaises(RuntimeError):
                await baseline.scan(guild,99,state,path=path,pause=0)
            saved = baseline.load(path)
            self.assertEqual((saved['cursor'],saved['scanned'],saved['recruits']),(100,100,100))
            with review.connect(path) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM baseline_week').fetchone()[0],0)
            broken = False
            await baseline.scan(guild,99,saved,path=path,pause=0)
            self.assertEqual(saved['status'],'complete')
            self.assertEqual(saved['recruits'],201)
            self.assertEqual(saved['scanned'],201)
            with review.connect(path) as db:
                rows = review.prior_counts(db,'2026-11-09')
            self.assertEqual(sum(map(sum,rows)),201)
            self.assertEqual(len(rows),len(saved['counts']))
            self.assertEqual(rows[0],[201,0,0,0,0,0,0])
            # A fresh import replaces the same weeks instead of adding counts.
            state = baseline.new_state(datetime(2026,11,11,12,tzinfo=timezone.utc))
            baseline.save(path,state)
            await baseline.scan(guild,99,state,path=path,pause=0)
            with review.connect(path) as db:
                self.assertEqual(sum(map(sum,review.prior_counts(db,'2026-11-09'))),201)

    async def test_command_starts_background_job_and_status_does_not_start_another(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.sqlite3'
            async def history(**kwargs):
                if False:
                    yield None
            guild = NS(id=review.GUILD_ID,me=NS(id=99),fetch_channel=AsyncMock(return_value=NS(history=history)))
            progress = NS(edit=AsyncMock())
            context = NS(guild=guild,send=AsyncMock(return_value=progress))
            await baseline.control(context,path=path,now=datetime(2026,11,11,12,tzinfo=timezone.utc))
            task = baseline.tasks[guild.id]
            await task
            self.assertEqual(baseline.load(path)['status'],'complete')
            await baseline.control(context,'status',path=path)
            self.assertIs(baseline.tasks[guild.id],task)
            self.assertIn('Baseline saved',context.send.call_args.args[0])
            baseline.tasks.pop(guild.id)
