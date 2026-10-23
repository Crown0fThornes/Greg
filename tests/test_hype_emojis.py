import ast
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import re
import unittest
from unittest.mock import AsyncMock, Mock

import discord

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT/'commands/commands.py').read_text())
NAMES = {'_hype_emoji_key', '_parse_hype_emojis', '_load_hype_emojis', 'refresh_hype_emojis',
         'hype_announcement_reactions', 'hype_announcement'}
NODES = [node for node in TREE.body if getattr(node, 'name', None) in NAMES or
         isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and
         (t.id.startswith('_HYPE_') or t.id=='_hype_emoji_cache_lock') for t in node.targets)]
for node in NODES:
    if isinstance(node,ast.AsyncFunctionDef):
        node.decorator_list=[]


class HypeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.saved = {}
        self.now = 10000000
        self.source_messages = ['🔥<:hype:123456> 👩🏽‍🌾🇺🇸', '<a:dance:234567>🔥 1️⃣']
        self.scans = 0
        case = self
        class Channel:
            async def history(self, **kwargs):
                assert kwargs == dict(limit=None, oldest_first=True)
                case.scans += 1
                for content in case.source_messages:
                    yield NS(content=content)
        self.guild = NS(id=10, fetch_channel=AsyncMock(return_value=Channel()))
        def remember(key, value=Ellipsis):
            if value is Ellipsis:
                return deepcopy(self.saved.get(key))
            self.saved[key] = deepcopy(value)
            return value
        self.random = NS(choices=Mock(return_value=[1]), sample=lambda values, count: list(values))
        self.env = dict(asyncio=asyncio, re=re, discord=discord, Context=object,
                        time=NS(time=lambda: self.now), remember=remember, random=self.random,
                        FF=NS(guild=10), traceback=NS(print_exc=Mock()))
        exec(compile(ast.Module(body=NODES,type_ignores=[]),'commands.py','exec'),self.env)

    def message(self, content='', roles=(), everyone=False, bot=False):
        return NS(guild=self.guild, content=content, role_mentions=[NS(id=rid) for rid in roles],
                  mention_everyone=everyone, author=NS(bot=bot), reactions=[],
                  add_reaction=AsyncMock(), channel=NS(id=1))

    def test_parser_preserves_joined_unicode_and_custom_tokens(self):
        result=self.env['_parse_hype_emojis']('🔥<:hype:123456><a:dance:234567>👩🏽‍🌾🇺🇸1️⃣🔥 ❤️❤')
        self.assertEqual(result, ['🔥','<:hype:123456>','<a:dance:234567>','👩🏽‍🌾','🇺🇸','1️⃣','❤️'])
        self.assertEqual(self.env['_parse_hype_emojis']('<:old:123456><:renamed:123456>'), ['<:old:123456>'])
        self.assertEqual(self.env['_parse_hype_emojis']('text and :not_an_emoji:'), [])

    async def test_all_messages_are_scanned_and_cache_survives_repeated_use(self):
        first=await self.env['_load_hype_emojis'](self.guild)
        self.assertEqual(len(first),6)
        self.assertEqual(await self.env['_load_hype_emojis'](self.guild),first)
        self.assertEqual(self.scans,1)
        self.assertEqual(next(iter(self.saved.values()))['emojis'],first)

    async def test_weekly_expiry_and_forced_refresh_pick_up_edits(self):
        await self.env['_load_hype_emojis'](self.guild)
        self.source_messages=['🎉']
        self.now+=7*86400
        self.assertEqual(await self.env['_load_hype_emojis'](self.guild), ['🎉'])
        self.source_messages=['🎊']
        self.assertEqual(await self.env['_load_hype_emojis'](self.guild,force=True), ['🎊'])
        self.assertEqual(self.scans,3)

    async def test_failed_refresh_preserves_previous_pool(self):
        before=await self.env['_load_hype_emojis'](self.guild)
        self.guild.fetch_channel.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'Missing access')
        self.assertEqual(await self.env['_load_hype_emojis'](self.guild,force=True), before)
        self.assertEqual(next(iter(self.saved.values()))['emojis'],before)

    async def test_mention_role_uses_inverse_count_weights(self):
        message=self.message(roles=[1181330910747054211])
        await self.env['hype_announcement_reactions'](message)
        message.add_reaction.assert_awaited_once()
        self.random.choices.assert_called_once_with([1,2,3,4,5],weights=[1,1/2,1/3,1/4,1/5],k=1)

    async def test_everyone_ping_from_bot_is_supported(self):
        message=self.message('@everyone great work',everyone=True,bot=True)
        self.random.choices.return_value=[5]
        await self.env['hype_announcement_reactions'](message)
        values=[call.args[0] for call in message.add_reaction.await_args_list]
        self.assertEqual(len(values),5)
        self.assertEqual(len(set(values)),5)

    async def test_nonping_everyone_text_and_here_do_not_trigger(self):
        for message in (self.message('@everyone',everyone=False), self.message('@here',everyone=True),
                        self.message(roles=[1234]),self.message('normal message')):
            await self.env['hype_announcement_reactions'](message)
            message.add_reaction.assert_not_awaited()
        self.guild.fetch_channel.assert_not_awaited()

    async def test_empty_pool_and_existing_bot_reaction(self):
        self.source_messages=[]
        message=self.message(roles=[1181330910747054211])
        await self.env['hype_announcement_reactions'](message)
        message.add_reaction.assert_not_awaited()
        self.source_messages=['🔥🎉']
        await self.env['_load_hype_emojis'](self.guild,force=True)
        message.reactions=[NS(emoji='🔥',me=True)]
        await self.env['hype_announcement_reactions'](message)
        message.add_reaction.assert_awaited_once_with('🎉')

    async def test_deleted_custom_emoji_falls_back_to_another(self):
        self.source_messages=['<:gone:123456>🎉']
        message=self.message(roles=[1181330910747054211])
        error=discord.NotFound(NS(status=404,reason='Not Found'),dict(code=10014,message='Unknown Emoji'))
        message.add_reaction.side_effect=[error,None]
        await self.env['hype_announcement_reactions'](message)
        self.assertEqual(message.add_reaction.await_count,2)
        self.assertEqual(message.add_reaction.await_args.args,('🎉',))

    async def test_missing_reaction_permission_stops_without_retry_spam(self):
        message=self.message(roles=[1181330910747054211])
        message.add_reaction.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'Missing permissions')
        await self.env['hype_announcement_reactions'](message)
        message.add_reaction.assert_awaited_once()

    async def test_weekly_job_forces_refresh(self):
        await self.env['_load_hype_emojis'](self.guild)
        self.source_messages=['🎉']
        await self.env['refresh_hype_emojis'](NS(get_guild=lambda _:self.guild))
        self.assertEqual(self.scans,2)

    async def test_production_listener_routes_bot_messages_to_hype_handler(self):
        tree=ast.parse((ROOT/'greg3.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='on_message')
        node.decorator_list=[]
        callback=AsyncMock()
        env=dict(commands=NS(hype_announcement_reactions=callback),CHANNEL_ID_DONT_RESPOND=999)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'greg3.py','exec'),env)
        message=self.message('@everyone',everyone=True,bot=True)
        await env['on_message'](message)
        callback.assert_awaited_once_with(message)


if __name__=='__main__':
    unittest.main()
