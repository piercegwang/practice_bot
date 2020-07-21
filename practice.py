import discord
from discord.ext import commands
import datetime
import json

room_ids = {}
with open('rooms.json') as json_file:
    room_ids = json.load(json_file)["rooms"]

print(list(room_ids.keys()))

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel and after.channel is not None: # User is joining or changing channel
            if str(after.channel.id) in list(room_ids.keys()):
                if room_ids[str(after.channel.id)]["practicing"] == 0 and len(after.channel.members) == 1: # No one is practicing yet
                    room_ids[str(after.channel.id)]["practicing"] = member
                    print("practicing set")
                    await member.edit(mute=False)
                else: # Someone is practicing or other people are already in the channel
                    await member.edit(mute=True)
            else:
                await member.edit(mute=False)

        elif after.channel is None and before.channel is not None: # User is leaving a channel
            if str(before.channel.id) in list(room_ids.keys()):
                if room_ids[str(before.channel.id)]["practicing"] == member: # Person leaving the channel is the person practicing
                    room_ids[str(before.channel.id)]["practicing"] = 0

                    if room_ids[str(before.channel.id)]["started_time"] != 0: # They started a practice session
                        duration = (datetime.datetime.now() - room_ids[str(before.channel.id)]["started_time"]).total_seconds()
                        duration = (int(duration / 3600), (duration % 3600)/60) #Not doing anything with this time yet
                        room_ids[str(before.channel.id)]["started_time"] = 0 #reset time
    
    @commands.command(pass_context=True)
    async def practice(self, ctx):
        """Start a practice session."""
        member = ctx.author
        if member.voice == None:
            await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        elif str(member.voice.channel.id) in list(room_ids.keys()):
            print("member is in voice")
            if (room_ids[str(member.voice.channel.id)]["practicing"] == member or room_ids[str(member.voice.channel.id)]["practicing"] == 0) and room_ids[str(member.voice.channel.id)]["started_time"] == 0:
                room_ids[str(member.voice.channel.id)]["started_time"] = datetime.datetime.now()
                room_ids[str(member.voice.channel.id)]["practicing"] = member
                await member.edit(mute=False)
                await ctx.send(member.mention + ", [X] You are now practicing.")
            else:
                await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
        else:
            await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
                

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        """Stop a practice session."""
        member = ctx.author
        if member.voice == None:
            await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        elif str(member.voice.channel.id) in list(room_ids.keys()):
            if room_ids[str(member.voice.channel.id)]["practicing"] == member and room_ids[str(member.voice.channel.id)]["started_time"] != 0:
                duration = (datetime.datetime.now() - room_ids[str(member.voice.channel.id)]["started_time"]).total_seconds()
                duration = [int(duration / 3600), (duration % 3600)/60]
                room_ids[str(member.voice.channel.id)]["started_time"] = 0
                room_ids[str(member.voice.channel.id)]["practicing"] = 0
                await member.edit(mute=True)
                await ctx.send(member.mention +  ", [ ] You're no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\nThe user practiced for " + str(duration[0]) + " hours and " + str(duration[1]) + " minutes")
            else:
                await ctx.send(member.mention + ", [ ] No practice session currently exists. You may not yet be practicing or someone else may be practicing!")
        else:
            await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        

    @commands.group(pass_context=True)
    async def cool(self, ctx):
        """Says if a user is cool."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Yeah, {0.subcommand_passed}'s cool.".format(ctx))

    @cool.command(name='bot')
    async def _bot(self):
        """Is the bot cool?"""
        await self.bot.say('Yes, the bot is cool.')

def setup(bot):
    bot.add_cog(Practice(bot))
