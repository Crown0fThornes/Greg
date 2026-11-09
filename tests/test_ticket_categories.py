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
