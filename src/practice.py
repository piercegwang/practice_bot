import discord
from discord.ext import commands
import datetime
import pickle

with open('../data/database.pickle', rb) as pickling_off:
    database_template = pickle.load(pickling_off)
    database = database_template

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild.id in database:
            if before.channel != after.channel and after.channel is not None: # User is joining or changing channel
                if after.channel.id in database[member.guild.id]:
                    if database[member.guild.id][after.channel.id]["practicing"] == 0 and len(after.channel.members) == 1: # No one is practicing yet
                        database[member.guild.id][after.channel.id]["practicing"] = member
                        print(member.mention + " is unofficially practicing")
                        await member.edit(mute=False)
                    else: # Someone is practicing or other people are already in the channel
                        await member.edit(mute=True)
                else:
                    await member.edit(mute=False)

            elif after.channel is None and before.channel is not None: # User is leaving a channel
                if before.channel.id in database[member.guild.id]:
                    if database[member.guild.id][before.channel.id]["practicing"] == member: # Person leaving the channel is the person practicing
                        database[member.guild.id][before.channel.id]["practicing"] = 0

                        if database[member.guild.id][before.channel.id]["started_time"] != 0: # They started a practice session
                            duration = (datetime.datetime.now() - database[member.guild.id][before.channel.id]["started_time"]).total_seconds()
                            duration = (int(duration / 3600), (duration % 3600)/60) #Not doing anything with this time yet
                            database[member.guild.id][before.channel.id]["started_time"] = 0 #reset time
                    elif len(before.channel.members) == 0: # No one left in the channel
                        database[member.guild.id][before.channel.id]["practicing"] = 0
                        
    
    @commands.command(pass_context=True)
    async def practice(self, ctx):
        """Start a practice session."""
        member = ctx.author
        if member.guild.id in database:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            elif member.voice.channel.id in database[member.guild.id]:
                print("member is in voice")
                if (database[member.guild.id][member.voice.channel.id]["practicing"] == member or room_ids[member.voice.channel.id]["practicing"] == 0) and room_ids[member.voice.channel.id]["started_time"] == 0:
                    database[member.guild.id][member.voice.channel.id]["started_time"] = datetime.datetime.now()
                    database[member.guild.id][member.voice.channel.id]["practicing"] = member
                    await member.edit(mute=False)
                    await ctx.send(member.mention + ", [X] You are now practicing.")
                else:
                    await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
            else:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        else:
            ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def stop(self, ctx):
        """Stop a practice session."""
        member = ctx.author
        if member.guild.id in database:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            elif member.voice.channel.id in database[member.guild.id]:
                if database[member.guild.id][member.voice.channel.id]["practicing"] == member and database[member.guild.id][member.voice.channel.id]["started_time"] != 0:
                    duration = (datetime.datetime.now() - database[member.guild.id][member.voice.channel.id]["started_time"]).total_seconds()
                    duration = [int(duration / 3600), (duration % 3600)/60]
                    database[member.guild.id][member.voice.channel.id]["started_time"] = 0
                    database[member.guild.id][member.voice.channel.id]["practicing"] = 0
                    await member.edit(mute=True)
                    await ctx.send(member.mention +  ", [ ] You're no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\nThe user practiced for " + str(duration[0]) + " hours and " + str(duration[1]) + " minutes")
                else:
                    await ctx.send(member.mention + ", [ ] No practice session currently exists. You may not yet be practicing or someone else may be practicing!")
            else:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        else:
            ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def add_practice_room(self, ctx, channel_id):
        try int(channel_id):
            channel_id = int(channel_id)
            if ctx.author.guild.id in database:
                database_template[ctx.author.guild.id][channel_id] = {"practicing": 0, "started_time": 0}
                database[ctx.author.guild.id][channel_id] = {"practicing": 0, "started_time": 0}
            else:
                database_template[ctx.author.guild.id] = {channel_id: {"practicing": 0, "started_time": 0}}
                database[ctx.author.guild.id] = {channel_id: {"practicing": 0, "started_time": 0}}
            with open('database.pickle', wb) as pickling_on:
                pickle.dump(database_template, pickling_on)
        except:
            ctx.send("Please enter a valid channel id!")


def setup(bot):
    bot.add_cog(Practice(bot))
