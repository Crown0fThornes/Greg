from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock,Mock,patch

import discord
import ticket_manager as tickets


class CategoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.data={}
        def remember(key,value=Ellipsis,delete=False):
            if value is None or delete:
                return self.data.pop(key,None)
            if value is not Ellipsis:
                self.data[key]=value
                return value
            return self.data.get(key)
        self.patch=patch.object(tickets,'remember',side_effect=remember)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.channels=[]
        self.guild=NS(id=1,fetch_channels=AsyncMock(side_effect=lambda:list(self.channels)))
        async def create(**kwargs):
            category=self.category(999,kwargs['name'])
            category.overwrites=kwargs['overwrites']
            return category
        self.guild.create_category_channel=AsyncMock(side_effect=create)

    def category(self,uid,name):
        category=Mock(spec=discord.CategoryChannel)
        category.id,category.name,category.position=uid,name,uid
        category.overwrites={'private':'permissions'}
        category.delete=AsyncMock(side_effect=lambda **kwargs:self.channels.remove(category))
        self.channels.append(category)
        return category

    def channel(self,uid,category):
        channel=Mock(spec=discord.TextChannel)
        channel.id,channel.category_id=uid,category.id
        self.channels.append(channel)
        return channel

    async def test_deleted_category_ids_are_pruned_without_fetching_them(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        ticket=self.channel(7,base)
        self.data['archive_categories']=[base.id,444,555]
        result=await tickets.get_all_closed_tickets(self.guild)
        self.assertEqual(result,[ticket])
        self.assertEqual(self.data['archive_categories'],[base.id])

    async def test_reuses_space_in_earlier_category_before_creating(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        overflow=self.category(2,'closed-tickets-2')
        for uid in range(50):
            self.channel(100+uid,overflow)
        self.assertIs(await tickets.ensure_category_capacity(self.guild),base)
        self.guild.create_category_channel.assert_not_awaited()

    async def test_full_category_creates_overflow_with_matching_permissions(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        for uid in range(50):
            self.channel(100+uid,base)
        result=await tickets.ensure_category_capacity(self.guild)
        self.assertEqual(result.id,999)
        self.assertEqual(self.guild.create_category_channel.call_args.kwargs['overwrites'],base.overwrites)
        self.assertIn(999,self.data['archive_categories'])

    async def test_no_closed_categories_uses_open_permission_template_on_demand(self):
        base=self.category(tickets.BASE_OPEN,'open-tickets')
        self.assertEqual(await tickets.get_all_closed_tickets(self.guild),[])
        result=await tickets.ensure_category_capacity(self.guild)
        self.assertEqual(result.overwrites,base.overwrites)

    async def test_cleanup_only_deletes_empty_overflow_and_retains_base(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        empty=self.category(2,'closed-tickets-2')
        occupied=self.category(3,'closed-tickets-3')
        unrelated=self.category(4,'Other category')
        self.channel(8,occupied)
        await tickets.cleanup_ticket_categories(self.guild)
        empty.delete.assert_awaited_once()
        base.delete.assert_not_awaited()
        occupied.delete.assert_not_awaited()
        unrelated.delete.assert_not_awaited()
        self.assertNotIn(empty.id,self.data['archive_categories'])

    def unsupported_type(self,payload):
        self.guild.fetch_channels.side_effect=discord.InvalidData('Unknown channel type 20')
        self.guild._state=NS(http=NS(get_all_guild_channels=AsyncMock(return_value=payload)))
        def factory(kind):
            if kind==20:
                return None,20
            return lambda **kwargs:next(channel for channel in self.channels
                                        if channel.id==int(kwargs['data']['id'])),kind
        return patch.object(tickets,'_guild_channel_factory',side_effect=factory)

    async def test_unknown_type_does_not_block_ticket_discovery(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        ticket=self.channel(7,base)
        payload=[dict(id=str(base.id),type=4),dict(id='7',type=0),
                 dict(id='1569594861953486856',type=20,parent_id=None)]
        with self.unsupported_type(payload):
            self.assertEqual(await tickets.get_all_closed_tickets(self.guild),[ticket])
        self.assertEqual(self.data['archive_categories'],[base.id])

    async def test_unknown_child_counts_towards_category_capacity(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        payload=[dict(id=str(base.id),type=4)]
        for uid in range(49):
            self.channel(100+uid,base)
            payload.append(dict(id=str(100+uid),type=0))
        payload.append(dict(id='500',type=20,parent_id=str(base.id)))
        with self.unsupported_type(payload):
            result=await tickets.ensure_category_capacity(self.guild)
        self.assertEqual(result.id,999)
        self.guild.create_category_channel.assert_awaited_once()

    async def test_cleanup_retains_category_with_unknown_child(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        occupied=self.category(2,'closed-tickets-2')
        payload=[dict(id=str(base.id),type=4),dict(id='2',type=4),
                 dict(id='500',type=20,parent_id='2')]
        with self.unsupported_type(payload):
            await tickets.cleanup_ticket_categories(self.guild)
        occupied.delete.assert_not_awaited()

    async def test_cleanup_rechecks_for_new_unknown_child_before_deleting(self):
        base=self.category(tickets.BASE_CLOSED,'closed-tickets')
        occupied=self.category(2,'closed-tickets-2')
        payload=[dict(id=str(base.id),type=4),dict(id='2',type=4),
                 dict(id='500',type=20,parent_id='2')]
        with self.unsupported_type(payload):
            # First response has no child; the fresh pre-delete response has it.
            self.guild._state.http.get_all_guild_channels.side_effect=[payload[:2],payload,payload,payload,payload]
            await tickets.cleanup_ticket_categories(self.guild)
        occupied.delete.assert_not_awaited()

    async def test_http_failure_is_not_treated_as_empty_server(self):
        self.guild.fetch_channels.side_effect=discord.Forbidden(NS(status=403,reason='Forbidden'),'blocked')
        with self.assertRaises(discord.Forbidden):
            await tickets.category_snapshot(self.guild)
        self.assertEqual(self.data,{})

    async def test_fallback_constructs_real_supported_channels(self):
        payload=[dict(id=str(tickets.BASE_CLOSED),type=4,name='closed-tickets',position=0),
                 dict(id='7',type=0,name='ticket',topic='123',position=1,parent_id=str(tickets.BASE_CLOSED)),
                 dict(id='8',type=20,parent_id=None)]
        self.guild.fetch_channels.side_effect=discord.InvalidData('Unknown channel type 20')
        self.guild._state=NS(http=NS(get_all_guild_channels=AsyncMock(return_value=payload)))
        result=await tickets.get_all_closed_tickets(self.guild)
        self.assertEqual(len(result),1)
        self.assertIsInstance(result[0],discord.TextChannel)
        self.assertEqual(result[0].topic,'123')
