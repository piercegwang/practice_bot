import discord
from discord.ext import commands
import datetime
import pickle

with open('../data/database.pickle', "rb") as pickling_off:
    database_template = pickle.load(pickling_off)
    database = dict(database_template)

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Test if a member is joining or leaving a practice channel. This function will take care of the initial unofficial practice session and other cases.
        """
        if member.guild.id in database and before.channel != after.channel:
            # Checking if there is a dictionary entry for the given guild and if there has been a channel change
            if after.channel is not None: # User is joining a channel
                if after.channel.id in database[member.guild.id]:
                    if database[member.guild.id][after.channel.id]["practicing"] == 0 and len(after.channel.members) == 1: # No one is practicing yet
                        database[member.guild.id][after.channel.id]["practicing"] = member
                        print(member.mention + " is unofficially practicing")
                        await member.edit(mute=False)
                    else: # Someone is practicing or other people are already in the channel
                        await member.edit(mute=True)
                else:
                    await member.edit(mute=False)

            if before.channel is not None: # User is leaving a channel
                if before.channel.id in database[member.guild.id]:
                    if database[member.guild.id][before.channel.id]["practicing"] == member: # Person leaving the channel is the person practicing
                        database[member.guild.id][before.channel.id]["practicing"] = 0
                        database[member.guild.id][before.channel.id]["song"] = ""
                        if len(before.channel.members) > 0:
                            for user in before.channel.members:
                                await user.edit(mute=True)

                        if database[member.guild.id][before.channel.id]["started_time"] != 0: # They had a practice session
                            duration = (datetime.datetime.now() - database[member.guild.id][before.channel.id]["started_time"]).total_seconds()
                            duration = (str(int(duration / 3600)), str(int((duration % 3600)/60)))
                            database[member.guild.id][before.channel.id]["started_time"] = 0 #reset time
                            database[member.guild.id][before.channel.id]["song"] = ""

                    elif len(before.channel.members) == 0: # No one left in the channel
                        database[member.guild.id][before.channel.id]["practicing"] = 0
                        database[member.guild.id][before.channel.id]["song"] = ""
    
    @commands.command(pass_context=True)
    async def practice(self, ctx):
        """Start a practice session."""
        member = ctx.author
        if member.guild.id in database:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            elif member.voice.channel.id in database[member.guild.id]:
                print("member is in voice")
                if (database[member.guild.id][member.voice.channel.id]["practicing"] == member or database[member.guild.id][member.voice.channel.id]["practicing"] == 0) and database[member.guild.id][member.voice.channel.id]["started_time"] == 0:
                    database[member.guild.id][member.voice.channel.id]["started_time"] = datetime.datetime.now()
                    database[member.guild.id][member.voice.channel.id]["practicing"] = member
                    await member.edit(mute=False)
                    await ctx.send(member.mention + ", [X] You are now practicing.")
                else:
                    await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
            else:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

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
                    duration = (str(int(duration / 3600)), str(int((duration % 3600)/60)))
                    database[member.guild.id][member.voice.channel.id]["started_time"] = 0
                    database[member.guild.id][member.voice.channel.id]["practicing"] = 0
                    database[member.guild.id][member.voice.channel.id]["song"] = ""
                    await member.edit(mute=True)
                    await ctx.send(member.mention +  ", [ ] You're no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\nThe user practiced for " + duration[0] + " hours and " + duration[1] + " minutes")
                else:
                    await ctx.send(member.mention + ", [ ] No practice session currently exists. You may not yet be practicing or someone else may be practicing!")
            else:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def add_practice_room(self, ctx, channel_id):
        if channel_id.isdigit():
            channel_id = int(channel_id)
            if ctx.author.guild.id in database:
                database_template[ctx.author.guild.id][channel_id] = {"practicing": 0, "started_time": 0, "song": ""}
                database[ctx.author.guild.id][channel_id] = {"practicing": 0, "started_time": 0, "song": ""}
            else:
                database_template[ctx.author.guild.id] = {channel_id: {"practicing": 0, "started_time": 0, "song": ""}}
                database[ctx.author.guild.id] = {channel_id: {"practicing": 0, "started_time": 0, "song": ""}}
            print(database)
            print(database_template)
            with open('../data/database.pickle', "wb") as pickling_on:
                pickle.dump(database_template, pickling_on)
            await ctx.send("Practice room added.")
        else:
            await ctx.send("Please enter a valid channel id!")

    @commands.command(pass_context=True)
    async def song(self, ctx, given_song):
        member = ctx.author
        if member.guild.id in database and member.voice != None:
            if member.voice.channel.id in database[member.guild.id] and database[member.guild.id][member.voice.channel.id]["practicing"] == member and database[member.guild.id][member.voice.channel.id]["started_time"] != 0:
                database[member.guild.id][member.voice.channel.id]["song"] = given_song
                await ctx.send(member.mention + ", song set.")
            else:
                await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def np(self, ctx):
        member = ctx.author
        if member.guild.id in database and member.voice != None:
            if member.voice.channel.id in database[member.guild.id] and database[member.guild.id][member.voice.channel.id]["practicing"] != 0 and database[member.guild.id][member.voice.channel.id]["started_time"] != 0:
                duration = (datetime.datetime.now() - database[member.guild.id][member.voice.channel.id]["started_time"]).total_seconds()
                duration = (str(int(duration / 3600)), str(int((duration % 3600)/60))) #Not doing anything with this time yet
                if database[member.guild.id][member.voice.channel.id]["song"] == "":
                    await ctx.send(member.mention + ", " + database[member.guild.id][member.voice.channel.id]["practicing"].display_name + " has been practicing for " + duration[0] + " hours and " + duration[1] + " minutes")
                else:
                    await ctx.send(member.mention + ", " + database[member.guild.id][member.voice.channel.id]["practicing"].display_name + " has been practicing " + database[member.guild.id][member.voice.channel.id]["song"] + " for " + duration[0] + " hours and " + duration[1] + " minutes")
                    
            else:
                await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def excuse(self, ctx, mention):
        member = ctx.author
        if member.guild.id in database and member.voice != None: # The guild id is in the database and the member is in a voice channel
            if member.voice.channel.id in database[member.guild.id] and database[member.guild.id][member.voice.channel.id]["practicing"] == member: # the member is in a practice channel and he/she is the one practicing
                if len(ctx.message.mentions) > 0:
                    await ctx.message.mentions[0].edit(mute=False)
                    await ctx.send(ctx.message.mentions[0].mention + " excused.")
            else:
                await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")

    @commands.command(pass_context=True)
    async def unexcuse(self, ctx, mention):
        member = ctx.author
        if member.guild.id in database and member.voice != None: # The guild id is in the database and the member is in a voice channel
            if member.voice.channel.id in database[member.guild.id] and database[member.guild.id][member.voice.channel.id]["practicing"] == member: # the member is in a practice channel and he/she is the one practicing
                if len(ctx.message.mentions) > 0:
                    await ctx.message.mentions[0].edit(mute=True)
                    await ctx.send(ctx.message.mentions[0].mention + " unexcused.")
            else:
                await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")
        else:
            await ctx.send("This guild does not have any practice rooms yet! Please contact your administrator.")
        

def setup(bot):
    bot.add_cog(Practice(bot))
