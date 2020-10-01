#!/usr/bin/env python

import discord
from discord.ext import commands
import logging
import json
import asyncio
import os
import asyncpg
import ssl

DATABASE_URL = os.environ['DATABASE_URL']

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='../output/discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

description = """I am a Discord Bot made by Pierce Wang specifically for practice rooms in Heifetz. Do $help for the list of my commands.
In order to get started, just join one of the practice rooms on the side and start a practice session using the command below (with a '$' in front of it)!"""

bot = commands.Bot(command_prefix='$', description=description)
bot.remove_command('help')

async def create_connection_pool():
    ctx = ssl.create_default_context(cafile='')
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    bot.pg_conn = await asyncpg.create_pool(DATABASE_URL,ssl=ctx)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    game = discord.Game(name='$help')
    await bot.change_presence(status=discord.Status.online, activity=game)
    await create_connection_pool()

@bot.command()
async def help(ctx):
    embed=discord.Embed(title="Help", description="To get started, simply join one of the designated practicing channels!", color=0x3c7f61)
    embed.set_author(name="Discord Practice Bot")
    embed.add_field(name="$practice", value="If no one is practicing yet, use $practice to start practicing.", inline=False)
    embed.add_field(name="$song", value="If you are practicing, you can use this command to set the song you are practicing. Usage: $song <song name>", inline=False)
    embed.add_field(name="$excuse", value="Unmutes a user so they can talk / give you feedback. Usage: $excuse", inline=False)
    embed.add_field(name="$unexcuse", value="Mutes a user once they are done giving feedback.", inline=False)
    embed.add_field(name="$userlimit", value="Set the user limit for a channel.", inline=False)
    embed.add_field(name="$break", value="Breaks are healthy! If you need to take a break, type $break and the bot will pause your timer so you can rest. During breaks, feel free to $excuse yourself if you would like to continue talking.", inline=False)
    embed.add_field(name="$resume", value="Continue practicing when you're done taking a break!", inline=False)
    embed.add_field(name="$np", value="This command will tell you information about the user practicing.", inline=False)
    embed.add_field(name="$stop", value="If you don't want to practice anymore, you can use $stop to tell the bot that you are done practicing.", inline=False)
    embed.add_field(name="$stats", value="Total time practiced is tracked by this bot. Query your stats using the $stats command. You can also check the stats of someone else by mentioning them using this command. Usage: $stats (optional) @mention", inline=False)
    embed.set_footer(text="Message will disappear in 40 seconds.")
    await ctx.send(embed=embed, delete_after = 40.0)

@bot.command()
async def credits(ctx):
    embed=discord.Embed(title="Credits", description="", color=0x3c7f61)
    embed.set_author(name="Creation", value = "This bot was made with love by Pierce using Discord.py. It was heavily inspired by Ray Chen's Discord's \"Shush bot\"", inline=True)
    await ctx.send(embed=embed, delete_after = 10.0)

@bot.command()
async def help_admin(ctx):
    embed=discord.Embed(title="Help", description="Server admin command guide.", color=0x3c7f61)
    embed.set_author(name="Discord Practice Bot")
    embed.add_field(name="$add_practice_room", value="Add a practice room. Each practice room must be linked to a text channel. Usage: $add_practice_room voice_channel_id text_channel_id", inline=False)
    embed.add_field(name="$remove_practice_room", value="Remove a practice room. Usage: $remove_practice_room voice_channel_id", inline=False)
    embed.set_footer(text="More to come! Message will disappear in 20 seconds.")
    await ctx.send(embed=embed, delete_after = 20.0)

bot.load_extension("practice")
bot.run(os.environ['BOT_TOKEN'])
