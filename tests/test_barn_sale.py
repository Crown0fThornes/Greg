import ast
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import discord

SOURCE=Path(__file__).resolve().parents[1]/'commands/commands.py'
NAMES=('open_barn_sale','choose_barn_sale_winner','close_barn_sale')


class BarnSaleTests(unittest.IsolatedAsyncioTestCase):
    def test_fixed_server_time_and_unchanged_spacing(self):
        nodes={node.name:node for node in ast.parse(SOURCE.read_text()).body if getattr(node,'name',None) in NAMES}
        for name,clock,day in zip(NAMES,('08:00','14:00','20:00'),(1,2,3)):
            decorator=nodes[name].decorator_list[0]
            self.assertEqual(ast.literal_eval(decorator.args[0]),clock)
            values={kw.arg:ast.literal_eval(kw.value) for kw in decorator.keywords}
            self.assertEqual(values,dict(day_of_month=day,timezone='Etc/GMT+4'))
        for month in (1,7):
            local=ZoneInfo('Etc/GMT+4')
            opening=datetime(2027,month,1,8,tzinfo=local).astimezone(timezone.utc)
            winner=datetime(2027,month,2,14,tzinfo=local).astimezone(timezone.utc)
            closing=datetime(2027,month,3,20,tzinfo=local).astimezone(timezone.utc)
            self.assertEqual(opening.hour,12)
            self.assertEqual((winner-opening).total_seconds(),30*3600)
            self.assertEqual((closing-winner).total_seconds(),30*3600)

    async def test_general_summary_has_participants_winner_and_prize(self):
        node=next(n for n in ast.parse(SOURCE.read_text()).body if getattr(n,'name',None)=='choose_barn_sale_winner')
        node.decorator_list=[]
        async def history(**kwargs):
            for _ in range(2):
                yield NS(author=NS(id=55,bot=False),attachments=[NS(content_type='image/png')])
        sale=NS(id=80,history=history,send=AsyncMock())
        general=NS(send=AsyncMock())
        guild=NS(fetch_channel=AsyncMock(side_effect=lambda cid:sale if cid==80 else general))
        env=dict(discord=discord,remember=lambda key:80,random=NS(choice=lambda sequence:sequence[0]))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),env)
        await env['choose_barn_sale_winner'](NS(get_guild=lambda gid:guild))
        content=general.send.call_args.args[0]
        self.assertIn('1 participants',content)
        self.assertIn('<@55>',content)
        self.assertIn('20 BEMs',content)
        self.assertIn('<#80>',content)
