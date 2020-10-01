import discord
from discord.ext import commands
import datetime
import os
import asyncpg

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # async def add_data(self, con, member_id, minutes):
    #     print(f'Adding data for {member_id}. {minutes} minutes')
    #     user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member_id)
    #     if user_info != None:
    #         async with con.transaction():
    #             await con.execute("UPDATE user_data SET total_practice = $1 WHERE member_id = $2", user_info["total_practice"] + minutes, member_id)
    #     else:
    #         async with con.transaction():
    #             await con.execute("INSERT INTO user_data VALUES ($1, $2)", member_id, minutes)
                
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
                            print(f'{member.nick} joined an empty channel')
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
                                duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                                user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member.id)
                                if user_info != None:
                                    async with con.transaction():
                                        await con.execute("UPDATE user_data SET total_practice = $1 WHERE member_id = $2", user_info["total_practice"] + duration, member.id)
                                else:
                                    async with con.transaction():
                                        await con.execute("INSERT INTO user_data VALUES ($1, $2)", member.id, duration)
                                        print(f'{member.name} left the channel and stopped their practice session.')
                                duration = (int(duration / 60), int((duration % 60)))
                                await self.bot.get_channel(practice_room["text_id"]).send(f'The person who was practicing left the channel. {member.nick} practiced {duration[0]} hours and {duration[1]} minutes.\nRoom: {before.channel.name}')
                                print(f'{member.nick} left the channel while practicing. They practiced {duration[0]} hours and {duration[1]} minutes.\nRoom: {before.channel.name}')
                            if len(before.channel.members) > 0: # Mute everyone in case someone was excused
                                for user in before.channel.members:
                                    await user.edit(mute=True)
                            await before.channel.edit(user_limit=69)
                        elif len(before.channel.members) == 0: # No one left in the channel
                            async with con.transaction():
                                await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", None, before.channel.id)
                                await con.execute("UPDATE practice_rooms SET minutes = $1 WHERE voice_id = $2", 0, member.voice.channel.id)
                            await before.channel.edit(user_limit=69)
    
    @commands.command(pass_context=True)
    async def practice(self, ctx):
        """Start a practice session."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if (practice_room["member"] == member.id or practice_room["member"] == None) and practice_room["started_time"] == None:
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", datetime.datetime.now(), member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", member.id, member.voice.channel.id)
                        await member.edit(mute=False)
                        await ctx.send(member.mention + ", [X] You are now practicing.")
                        print(f'{member.nick} started practice session')
                    else:
                        await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['break'])
    async def rest(self, ctx):
        """Take a break."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id and practice_room["started_time"] != None:
                        duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET minutes = $1 WHERE voice_id = $2", practice_room["minutes"] + duration, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                        await member.edit(mute=True)
                        duration = (int(duration / 60), int((duration % 60)))
                        await ctx.send(f'{member.mention}, [ ] You\'re taking a break.\n {member.nick} has practiced for {duration[0]} hours and {duration[1]} minutes')
                    else:
                        await ctx.send(member.mention + ", [ ] No practice session for you currently exists. You may not yet be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True)
    async def resume(self, ctx):
        """Resume from after a break."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if (practice_room["member"] == member.id or practice_room["member"] == None) and practice_room["started_time"] == None:
                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", datetime.datetime.now(), member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", member.id, member.voice.channel.id)
                        await member.edit(mute=False)
                        await ctx.send(member.mention + ", [X] You've resumed your practice session")
                        print(f'{member.nick} started practice session')
                    else:
                        await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['stop'])
    async def nomore(self, ctx):
        """Stop a practice session."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id:
                        if practice_room["started_time"] != None:
                            duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                        else: # On break, no started time or never started official practice session
                            duration = practice_room["minutes"]
                        user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member.id)
                        if user_info != None:
                            async with con.transaction():
                                await con.execute("UPDATE user_data SET total_practice = $1 WHERE member_id = $2", user_info["total_practice"] + duration, member.id)
                        else:
                            async with con.transaction():
                                await con.execute("INSERT INTO user_data VALUES ($1, $2)", member.id, duration)
                        duration = (int(duration / 60), int((duration % 60)))

                        async with con.transaction():
                            await con.execute("UPDATE practice_rooms SET member = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET started_time = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET song = $1 WHERE voice_id = $2", None, member.voice.channel.id)
                            await con.execute("UPDATE practice_rooms SET minutes = $1 WHERE voice_id = $2", 0, member.voice.channel.id)
                        await member.edit(mute=True)
                        await ctx.send(f'{member.mention}, [ ] You\'re no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\n {member.nick} practiced for {duration[0]} hours and {duration[1]} minutes')
                    else:
                        await ctx.send(member.mention + ", [ ] No practice session for you currently exists. You may not yet be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True)
    async def add_practice_room(self, ctx, channel_id, text_id):
        """Add a practice room, linked to a text channel"""
        async with self.bot.pg_conn.acquire() as con:
            if ctx.author.guild_permissions.administrator == False:
                await ctx.send("You do not have permission to run this command.")
            elif channel_id.isdigit() and text_id.isdigit():
                channel_id = int(channel_id)
                text_id = int(text_id)
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", channel_id)
                if practice_room == None:
                    async with con.transaction():
                        await con.execute("INSERT INTO practice_rooms VALUES ($1, $2, $3, $4, $5, $6)", channel_id, text_id, None, None, None, 0)
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
            if member.voice == None:
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
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["started_time"] != None:
                        duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                        duration = (int(duration / 60), int((duration % 60)))
                        if practice_room["song"] == None:
                            await ctx.send(f'{member.mention}, {ctx.guild.get_member(practice_room["member"]).display_name} has been practicing for {duration[0]} hours and {duration[1]} minutes')
                        else:
                            await ctx.send(member.mention + ", " + ctx.guild.get_member(practice_room["member"]).display_name + " has been practicing " + practice_room["song"] + " for " + duration[0] + " hours and " + duration[1] + " minutes")
                else:
                    await ctx.send(member.mention + ", [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!")

    @commands.command(pass_context=True)
    async def excuse(self, ctx, *, mentions):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None: # Member is not in a voice channel
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
    async def unexcuse(self, ctx, *, mentions):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None: # Member is not in a voice channel
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

    @commands.command(pass_context=True)
    async def userlimit(self, ctx, given_limit : int):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None: # Member is not in a voice channel
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id: # the member is in a practice channel and they are the one practicing
                        await member.voice.channel.edit(user_limit = given_limit)
                        await ctx.send(f'{member.mention}, user limit set to {given_limit}')
                    else:
                        await ctx.send(member.mention + ", you're not the one practicing!")

    @commands.command(pass_context=True)
    async def stats(self, ctx):
        member = ctx.author
        if len(ctx.message.mentions) > 0:
            user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", ctx.message.mentions[0].id)
            if user_info != None:
                embed = discord.Embed(title=f'{ctx.message.mentions[0].nick}\'s Stats')
                embed.add_field(name="Total Practice Time", value=f'Your total time practiced is: {int(user_info["total_practice"] / 60)} hours and {user_info["total_practice"] % 60} minutes.', inline=False)
                embed.set_footer(text="If you believe there is a mistake, please contact @Omar#4304. This message deletes after 20 seconds.")
                await ctx.send(embed=embed, delete_after = 20.0)
            else:
                await ctx.send(f'There is no data on {ctx.message.mentions[0].nick}!')
        else:
            user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member.id)
            if user_info != None:
                embed = discord.Embed(title=f'{member.nick}\'s Stats')
                embed.add_field(name="Total Practice Time", value=f'Your total time practiced is: {int(user_info["total_practice"] / 60)} hours and {user_info["total_practice"] % 60} minutes.', inline=False)
                embed.set_footer(text="If you believe there is a mistake, please contact @Omar#4304. This message deletes after 20 seconds.")
                await ctx.send(embed=embed, delete_after = 20.0)
            else:
                await ctx.send(f'We don\'t have any data on you!')



def setup(bot):
    bot.add_cog(Practice(bot))
