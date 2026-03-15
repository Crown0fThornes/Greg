from math import floor
from command_handler import Context, AccessType, CommandArgsError, PardonOurDustError
import command_handler
from custom_types import Neighbor, Item
from responses import ResponsePackage, ResponseRequest
import commands
import time
import random
import sqlite3
import json
import password_manager

nh_roles = {
    "pro": ,
    "main": ,
    "junior": ,
    "garden": ,
    "carnival": ,
    "resort": ,
}

@command_handler.Command(access_type=AccessType.PRIVILEGED)
async def create_rolode(activator: Neighbor, context: Context):
    
    joinlist_channel = await context.guild.fetch_channel(943263445724311572)
    leavelist_channel = await context.guild.fetch_channel(1138557740185305169)
    
    async for message in joinlist_channel.history(oldest_fr)