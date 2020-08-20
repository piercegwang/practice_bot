import discord
from discord.ext import commands
import datetime
import os
import asyncpg

# Database structure:
# class Room(Base):
#     __tablename__ = 'practice_rooms'
#     voice_id = Column(Integer, primary_key = True)
#     text_id = Column(Integer)
#     member = Column(Integer, nullable=True)
#     started_time = Column(DateTime, nullable=True)
#     song = Column(string(String(150)), nullable=True)

"""
self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", some_channel)
async with con.transaction():
    await con.execute("INSERT INTO user_settings VALUES ($1, $2, $3)", (id,name,0))
    await con.execute("UPDATE user_settings SET channel_name = $1 WHERE user_id = $2", name, id)
"""

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
                
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Test if a member is joining or leaving a practice channel. This function will take care of the initial unofficial practice session and other cases.
        """
        async with self.bot.pg_conn.acquire() as con:
            if before.channel != after.channel:
                # Checking if there is a dictionary entry for the given guild and if there has been a channel change
                if after.channel is not None: # User is joining a channel
                    practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", after.channel.id)
                    if practice_room != None:
                        if practice_room["member"] == None and len(after.channel.members) == 1: # No one is practicing yet
                            async with con.transaction():
                                await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", member.id, after.channel.id)
                            print(member.nick + " just started unofficially practicing")
                            await member.edit(mute=False)
                        else: # Someone is practicing or other people are already in the channel
                            await member.edit(mute=True)
                    else:
                        await member.edit(mute=False)

                if before.channel is not None: # User is leaving a channel
                    practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", before.channel.id)
                    if practice_room != None:
                        if practice_room["member"] == member.id: # Person leaving the channel is the person practicing
                            async with con.transaction():
                                await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", None, before.channel.id)
                            if practice_room["started_time"] != None: # They had a practice session
                                duration = (datetime.datetime.now() - practice_room["started_time"]).total_seconds()
                                duration = (str(int(duration / 3600)), str(int((duration % 3600)/60)))
                                await self.bot.get_channel(practice_room["text_id"]).send(f'The person who was practice left the channel. Practiced {duration[0]} hours and {duration[1]} minutes')
                                print(f'{member.nick} left the channel while practicing. They practiced {duration[0]} hours and {duration[1]} minutes')
                            if len(before.channel.members) > 0: # Mute everyone in case someone was excused
                                for user in before.channel.members:
                                    await user.edit(mute=True)
                        elif len(before.channel.members) == 0: # No one left in the channel
                            async with con.transaction():
                                await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", None, before.channel.id)
    
    @commands.command(pass_context=True)
    async def practice(self, ctx):
        """Start a practice session."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if (practice_room["member"] == member.id or practice_room["member"] == 0) and practice_room["started_time"] == None:
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", datetime.datetime.now(), member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", member.id, member.voice.channel.id)
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
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id and practice_room["started_time"] != None:
                        duration = (datetime.datetime.now() - practice_room["started_time"]).total_seconds()
                        duration = (str(int(duration / 3600)), str(int((duration % 3600)/60)))
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                        await member.edit(mute=True)
                        await ctx.send(member.mention +  ", [ ] You're no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\nThe user practiced for " + duration[0] + " hours and " + duration[1] + " minutes")
                    else:
                        await ctx.send(member.mention + ", [ ] No practice session for you currently exists. You may not yet be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True)
    async def add_practice_room(self, ctx, channel_id, text_id):
        async with self.bot.pg_conn.acquire() as con:
            if ctx.author.guild_permissions.administrator == False:
                await ctx.send("You do not have permission to run this command.")
            elif channel_id.isdigit() and text_id.isdigit():
                channel_id = int(channel_id)
                text_id = int(text_id)
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", channel_id)
                if practice_room == None:
                    async with con.transaction():
                        await con.execute("INSERT INTO practice_rooms VALUES ($1, $2, $3, $4, $5)", channel_id, text_id, None, None, None)
                    await ctx.send("Practice room added.")
                else:
                    await ctx.send("This practice room has already been added!")
            else:
                await ctx.send("Please enter valid voice and text channel ids!")

    @commands.command(pass_context=True)
    async def remove_practice_room(self, ctx, channel_id):
        async with self.bot.pg_conn.acquire() as con:
            if ctx.author.guild_permissions.administrator == False:
                await ctx.send("You do not have permission to run this command.")
            elif channel_id.isdigit():
                channel_id = int(channel_id)
                practice_room = await self.bot.pg_conn.fetchrow("Select * FROM practice_rooms WHERE voice_id = $1", channel_id)
                if practice_room != None:
                    async with con.transaction():
                        await con.execute("DELETE FROM practice_rooms WHERE voice_id = $1", channel_id)
                    await ctx.send("Practice room removed.")
                else:
                    await ctx.send("Practice room does not exist yet.")
            else:
                await ctx.send("Please enter a valid voice channel id.")

    @commands.command(pass_context=True)
    async def song(self, ctx, *, given_song : str):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id and practice_room["started_time"] != None:
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", given_song, member.voice.channel.id)
                        await ctx.send(member.mention + ", song set.")
                    else:
                        await ctx.send(member.mention + ", [ ] You must be in an official practice session to run this command! If no one else is practicing in this channel, then type $practice to start a session!")

    @commands.command(pass_context=True)
    async def np(self, ctx):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["started_time"] != None:
                        duration = (datetime.datetime.now() - practice_room["started_time"]).total_seconds()
                        duration = (str(int(duration / 3600)), str(int((duration % 3600)/60)))
                        if practice_room["song"] == None:
                            await ctx.send(member.mention + ", " + ctx.guild.get_member(practice_room["member"]).display_name + " has been practicing for " + duration[0] + " hours and " + duration[1] + " minutes")
                        else:
                            await ctx.send(member.mention + ", " + ctx.guild.get_member(practice_room["member"]).display_name + " has been practicing " + practice_room["song"] + " for " + duration[0] + " hours and " + duration[1] + " minutes")

                else:
                    await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")

    @commands.command(pass_context=True)
    async def excuse(self, ctx, mention):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None: # Member is not in a voice channel
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id: # the member is in a practice channel and they are the one practicing
                        if len(ctx.message.mentions) > 0:
                            await ctx.message.mentions[0].edit(mute=False)
                            await ctx.send(ctx.message.mentions[0].mention + " excused.")
                        else:
                            await ctx.send(member.mention + ", please @mention someone to excuse!")
                    else:
                        await ctx.send(member.mention + ", you're not the one practicing!")

    @commands.command(pass_context=True)
    async def unexcuse(self, ctx, mention):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice.channel == None: # Member is not in a voice channel
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id: # the member is in a practice channel and they are the one practicing
                        if len(ctx.message.mentions) > 0:
                            await ctx.message.mentions[0].edit(mute=True)
                            await ctx.send(ctx.message.mentions[0].mention + " unexcused.")
                        else:
                            await ctx.send(member.mention + ", please @mention someone to unexcuse!")
                    else:
                        await ctx.send(member.mention + ", you're not the one practicing!")

def setup(bot):
    bot.add_cog(Practice(bot))
