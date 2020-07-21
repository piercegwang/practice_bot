#!/usr/bin/env python

import discord
from discord.ext import commands
import logging
import json
import asyncio

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
bot.remove_command('help')

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    # await bot.change_presence(game=discord.Game(name='Adobe Connect'))

@bot.command()
async def help(ctx):
    embed=discord.Embed(title="Help", description="A guide to the useful commands for the practice bot.", color=0x3c7f61)
    embed.set_author(name="Heifetz Practice Bot")
    embed.add_field(name="$practice", value="If no one is practicing yet, use $practice to start practicing.", inline=False)
    embed.add_field(name="$excuse", value="Unmutes a user so they can talk / give you feedback. Usage: $excuse", inline=False)
    embed.add_field(name="$unexcuse", value="Mutes a user once they are done giving feedback.", inline=False)
    embed.add_field(name="$stop", value="If you don't want to practice anymore, you can use $stop to tell the bot that you are done practicing.", inline=False)
    embed.add_field(name="$song", value="If you are practicing, you can use this command to set the song you are practicing. Usage: $song <song name>", inline=False)
    embed.add_field(name="$np", value="This command will tell you information about the user practicing.", inline=False)
    embed.set_footer(text="This message will disappear in 20 seconds.")
    await ctx.send(embed=embed, delete_after = 20.0)

bot.load_extension("practice")

bot.run(TOKEN)
