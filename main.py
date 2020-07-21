#!/usr/bin/env python

import discord
from discord.ext import commands
import logging
import json

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

TOKEN = ''
with open('../../tokens/heifetz_token.json') as json_file:
    atoken = json.load(json_file)
    TOKEN = atoken['token']


description = """I am a Discord Bot made by Pierce Wang specifically for practice rooms in Heifetz. Do ?help for the list of my commands."""

startup_extensions = ["practice_rooms"]

bot = commands.Bot(command_prefix='$', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    # await bot.change_presence(game=discord.Game(name='Adobe Connect'))

if __name__ == "__main__":
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

bot.run(TOKEN)
