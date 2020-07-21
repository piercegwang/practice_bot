#!/usr/bin/env python

import discord
from discord.ext import commands
import logging
import json

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='../output/discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

TOKEN = ''
with open('../../tokens/heifetz_token.json') as json_file:
    atoken = json.load(json_file)
    TOKEN = atoken['token']


description = """I am a Discord Bot made by Pierce Wang specifically for practice rooms in Heifetz. Do $help for the list of my commands.
In order to get started, just join one of the practice rooms on the side and start a practice session using the command below (with a '$' in front of it)!"""

bot = commands.Bot(command_prefix='$', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    # await bot.change_presence(game=discord.Game(name='Adobe Connect'))

@bot.command
async def help(pass_context):
    

bot.load_extension("practice")

bot.run(TOKEN)
