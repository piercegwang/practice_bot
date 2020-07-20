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
with open('../../tokens/ohstoken.json') as json_file:
    atoken = json.load(json_file)
    TOKEN = atoken['token']


description = """Hello! I'm the *nearly official* discord bot for the OHS Community server. Do ?help for the list of my commands."""

startup_extensions = ["members", "rng"]

bot = commands.Bot(command_prefix='?', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    # await bot.change_presence(game=discord.Game(name='Adobe Connect'))

@bot.command()
async def load(extension_name : str):
    """Loads an extension."""
    try:
        bot.load_extension(extension_name)
    except (AttributeError, ImportError) as e:
        await bot.say("```py\n{}: {}\n```".format(type(e).__name__, str(e)))
        return
    await bot.say("{} loaded.".format(extension_name))
    print("{} loaded.".format(extension_name))


@bot.command()
async def unload(extension_name : str):
    """Unloads an extension."""
    bot.unload_extension(extension_name)
    await bot.say("{} unloaded.".format(extension_name))
    print("{} unloaded.".format(extension_name))


@bot.command(pass_context=True)
async def clear(ctx, num : int):
    """Deletes a given number of messages"""
    if "487772520791932928" in [y.id for y in ctx.message.author.roles]:
        mgs = [] #Empty list to put all the messages in the log
        async for x in bot.logs_from(ctx.message.channel, limit = num+1):
            mgs.append(x)
        if(num>=1 and num<=99):
            await bot.delete_messages(mgs)
        else:
            await bot.say("Please enter a number between 1-99!")
    else:
        logger.log(1, str(ctx.message.author) + " tried to delete messages in " + str(ctx.message.channel))
        await bot.say("You don't have the proper role for this command!")

@bot.command(pass_context=True)
async def beautifulembed(ctx):
    """Displays a test embed message"""
    channel = ctx.message.channel
    embed = discord.Embed(
        title = 'Embedded Message',
        description = 'This is absolutely useless...',
        colour=discord.Colour.blue()
    )
    
    embed.set_footer(text='less useless.')
    embed.set_author(name='Pierce Wang')
    embed.add_field(name='This is a Field', value='Field Value', inline=True)
    embed.add_field(name='This is a Field', value='Field False', inline=False)
    await bot.send_message(channel, embed=embed)

if __name__ == "__main__":
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

bot.run(TOKEN)
