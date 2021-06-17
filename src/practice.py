import discord
from discord.ext import commands
import datetime
import os
import asyncpg
import asyncio

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def edit_room(self, con, channel_id, properties, reason):
        """Documentation for edit_room: edits the room in the PostGreSQL database

        Args: con, channel_id, properties, reason
        :param con: an instance of self.bot.pg_conn.acquire()
        :param channel_id: a voice channel id to query the database
        :param properties: properties to change: member, started_time, song, minutes
        :param reason: A string to print in the log
        
        :returns: None
        :raises keyError: None
        """
        async with con.transaction():
            print(f'Editing practice_room database; {reason}')
            print(f'Editing room {channel_id}:')
            for key, value in properties.items():
                print(f'+ {key} = {value}')
                await con.execute(f'UPDATE practice_rooms SET {key} = $1 WHERE voice_id = $2', value, channel_id)
        print(f'--')

    async def add_time(self, con, member_id, minutes):
        """Documentation for add_time: adding time for a user in PostGreSQL database

        Args: con, member_id, minutes
        :param con: an instance of self.bot.pg_conn.acquire()
        :param member_id: a member id to query in database
        :param minutes: minutes to add to their time
        
        :returns: None
        :raises keyError: None
        """
        user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member_id)
        print(f'Editing user {member_id}')
        async with con.transaction():
            print(f'+ minutes += {minutes}')
            if user_info != None:
                await con.execute("UPDATE user_data SET total_practice = $1 WHERE member_id = $2", user_info["total_practice"] + minutes, member_id)
            else:
                await con.execute("INSERT INTO user_data VALUES ($1, $2)", member_id, minutes)

    async def try_mute(self, member, mute):
        """Documentation for try_mute: wrapping try-catch block around mute

        Args: member, mute
        :param member: a member object
        :param mute: a boolean describing whether to mute or unmute the member
        
        :returns: None
        :raises keyError: None
        """
        try:
            await member.edit(mute=mute)
        except:
            print(f'No permission to mute/unmute user on {member.guild.name}')
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Test if a member is joining or leaving a practice channel. This function will take care of the initial unofficial practice session and other cases.
        """
        async with self.bot.pg_conn.acquire() as con:
            if before.channel != after.channel:
                if after.channel is not None: # User is joining a channel
                    num_members_after = len(after.channel.members)
                    print(f'Before: number of members left in channel: {num_members_after}')
                    practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", after.channel.id)
                    if practice_room != None:
                        if practice_room["member"] == None and num_members_after == 1: # No one is practicing yet
                            await self.edit_room(con, after.channel.id, {"member": member.id}, f'{member.display_name} joined an empty channel')
                            await self.try_mute(member, False)
                        else: # Someone is practicing or other people are already in the channel
                            await self.try_mute(member, True)
                    else:
                        try:
                            await self.try_mute(member, False)
                        except:
                            print(f'No permission to mute user on {member.guild.name}')

                if before.channel is not None: # User is leaving a channel
                    members_before = before.channel.members
                    num_members_before = len(members_before)
                    print(f'After: number of members left in the channel: {num_members_before}')
                    print(f'Users left: {members_before}')
                    practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", before.channel.id)
                    if practice_room != None:
                        if practice_room["member"] == member.id: # Person leaving the channel is the person practicing
                            await self.edit_room(con, before.channel.id, {"member": None, "started_time": None, "song": None, "minutes": 0}, f'{member.display_name} left the channel while practicing')
                            if practice_room["started_time"] != None or practice_room["minutes"] > 0: # They had a practice session
                                if practice_room["started_time"] != None:
                                    duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                                else:
                                    duration = practice_room["minutes"]
                                await self.add_time(con, member.id, duration)
                                print(f'{member.name} left the channel and stopped their practice session.')
                                duration = (int(duration / 60), int((duration % 60)))
                                await self.bot.get_channel(practice_room["text_id"]).send(f'The person who was practicing left the channel. {member.display_name} practiced {duration[0]} hours and {duration[1]} minutes.\nRoom: {before.channel.name}')
                                print(f'{member.display_name} left the channel while practicing. They practiced {duration[0]} hours and {duration[1]} minutes.\nRoom: {before.channel.name}')
                            else:
                                print(f'{member.display_name} left the channel while practicing.')
                            if num_members_before > 0: # Mute everyone in case someone was excused
                                for user in members_before:
                                    await user.edit(mute=True)
                            await before.channel.edit(user_limit = 99)
                            await before.channel.edit(bitrate = 96000)
                        elif num_members_before == 0: # No one left in the channel
                            await self.edit_room(con, before.channel.id, {"member": None, "started_time": None, "song": None, "minutes": 0}, f'{member.display_name} left and the channel is now empty')
                            await before.channel.edit(user_limit=99)
                            await before.channel.edit(bitrate = 96000)
    
    @commands.command(pass_context=True, aliases=['p'])
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
                        await self.edit_room(con, member.voice.channel.id, {"started_time": datetime.datetime.now(), "member": member.id}, f'{member.display_name} is now practicing')
                        await self.try_mute(member, False)
                        await ctx.send(member.mention + ", [X] You are now practicing.")
                        print(f'{member.display_name} started practice session')
                    else:
                        await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['break', 'b'])
    async def rest(self, ctx, time=None):
        """Take a break. Use with a time argument (in minutes) to take a timed break."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id and practice_room["started_time"] != None:
                        duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                        await self.edit_room(con, member.voice.channel.id, {"minutes": duration, "started_time": None}, f'{member.display_name} is now resting.')
                        duration = (int(duration / 60), int((duration % 60)))
                        if not time:
                            await ctx.send(f'{member.mention}, [ ] You\'re taking a break of indefinite time.\n {member.display_name} has practiced for {duration[0]} hours and {duration[1]} minutes.\n**Remember to type `$resume` when you start practicing again!**\n\nIf you want to take a timed break next time, please use `$break <time in minutes>`. E.g. `$break 10` for a 10-minute break.')
                        elif time.isnumeric():
                            wait = 60 * int(time)
                            await ctx.send(f'{member.mention}, [ ] You\'re taking a {time} minute break.\n {member.display_name} has practiced for {duration[0]} hours and {duration[1]} minutes.\nYou\'ll be pinged in {time} minutes.')
                            await asyncio.sleep(wait)
                            practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                            if practice_room["member"] == member.id and practice_room["started_time"] == None:
                                await ctx.send(f'{member.mention}, *nudge*, Your {time} minute timer to start your practice session has ended!')
                            if practice_room["member"] == member.id and practice_room["started_time"] != None:
                                await ctx.send(f'{member.mention}, Your {time} minute timer to start you practice session has ended, but you\'re already practicing. Good for you!')
                    elif practice_room["member"] == member.id and practice_room["duration"] > 0:
                        await ctx.send(member.mention + ", [ ] You're already on a break! Do `$resume` to continue your practice session.")
                    else:
                        await ctx.send(member.mention + ", [ ] No practice session for you currently exists. You may not yet be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['r'])
    async def resume(self, ctx):
        """Resume from after a break."""
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if (practice_room["member"] == member.id) and practice_room["started_time"] == None:
                        await self.edit_room(con, member.voice.channel.id, {"started_time": datetime.datetime.now(), "member": member.id}, f'{member.display_name} has resumed their practice session.')
                        await ctx.send(f'{member.mention}, [X] You\'re practice session has been resumed')
                        print(f'{member.display_name} started practice session')
                    else:
                        await ctx.send(member.mention + ", [ ] Practice session not started. You may already be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['nomore', 'n', 'st'])
    async def stop(self, ctx):
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
                        await self.add_time(con, member.id, duration)
                        duration = (int(duration / 60), int((duration % 60)))
                        await self.edit_room(con, member.voice.channel.id, {"member": None, "started_time": None, "song": None, "minutes": 0}, f'{member.display_name} $stop-ed their practice session.')
                        await member.edit(mute=True)
                        await ctx.send(f'{member.mention}, [ ] You\'re no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say \"$practice\" will be able to practice in this channel.\n {member.display_name} practiced for {duration[0]} hours and {duration[1]} minutes')
                    else:
                        await ctx.send(member.mention + ", [ ] No practice session for you currently exists. You may not yet be practicing or someone else may be practicing!")
                else:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")

    @commands.command(pass_context=True, aliases=['piece', 's'])
    async def song(self, ctx, *, given_song : str = ""):
        member = ctx.author
        if given_song != "":
            async with self.bot.pg_conn.acquire() as con:
                if member.voice == None:
                    await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
                else:
                    practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                    if practice_room != None:
                        if practice_room["member"] == member.id and (practice_room["started_time"] != None or practice_room["duration"] > 0):
                            await self.edit_room(con, member.voice.channel.id, {"song": given_song}, f'{member.display_name} changed the song.')
                            await ctx.send(member.mention + ", song set.")
                        else:
                            await ctx.send(member.mention + ", [ ] You must be in an official practice session to run this command! If no one else is practicing in this channel, then type $practice to start a session!")
        else:
            await ctx.send(f'{member.mention}, song not set. Please provide a song name')

    @commands.command(pass_context=True, aliases=['current'])
    async def np(self, ctx):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None:
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    print(f'Database member id currently: {practice_room["member"]}')
                    practicer = await ctx.guild.fetch_member(practice_room["member"])
                    if practicer == None and practice_room["member"] != None:
                        await ctx.send(f'{member.mention}, Someone is logged to be practicing at the moment, but the `get_member` function isn\'t working. Omar is working on fixing this now!')
                    if practice_room["started_time"] != None:
                        duration = int((datetime.datetime.now() - practice_room["started_time"]).total_seconds() / 60) + practice_room["minutes"]
                        duration = (int(duration / 60), int((duration % 60)))
                        if practice_room["song"] == None:
                            await ctx.send(f'{member.mention}, {practicer.display_name} has been practicing for {duration[0]} hours and {duration[1]} minutes')
                        else:
                            await ctx.send(f'{member.mention}, {practicer.display_name} has been practicing {practice_room["song"]} for {duration[0]} hours and {duration[1]} minutes')
                    elif practice_room["minutes"] > 0:
                        duration = practice_room["minutes"]
                        duration = (int(duration / 60), int((duration % 60)))
                        if practice_room["song"] == None:
                            await ctx.send(f'{member.mention}, {practicer.display_name} is taking a break and has been practicing for {duration[0]} hours and {duration[1]} minutes')
                        else:
                            await ctx.send(f'{member.mention}, {practicer.display_name} is taking a break and has been practicing {practice_room["song"]} for {duration[0]} hours and {duration[1]} minutes')
                    else:
                        await ctx.send(f'{member.mention}, the person practicing hasn\'t started an official practice session yet!')
                else:
                    await ctx.send(f'{member.mention}, [ ] You are either not in a practice channel or you are not in an official practice session. If it is the latter, then type $practice to start a session!')

    @commands.command(pass_context=True, aliases=['unmute', 'um'])
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

    @commands.command(pass_context=True, aliases=['mute', 'shush', 'mu'])
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

    @commands.command(pass_context=True, aliases=['limit', 'lim'])
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

    @commands.command(pass_context=True, aliases = ['bitrate'])
    async def setbit(self, ctx, bitrate : int):
        member = ctx.author
        async with self.bot.pg_conn.acquire() as con:
            if member.voice == None: # Member is not in a voice channel
                await ctx.send(member.mention + ", You must be in one of the practice room voice channels to use this command!")
            else:
                practice_room = await self.bot.pg_conn.fetchrow("SELECT * FROM practice_rooms WHERE voice_id = $1", member.voice.channel.id)
                if practice_room != None:
                    if practice_room["member"] == member.id: # the member is in a practice channel and they are the one practicing
                        await member.voice.channel.edit(bitrate = bitrate * 1000)
                        await ctx.send(f'{member.mention}, voice channel bitrate set to {bitrate}')
                    else:
                        await ctx.send(member.mention + ", you're not the one practicing!")

    @commands.command(pass_context=True)
    async def stats(self, ctx):
        member = ctx.author
        if len(ctx.message.mentions) > 0:
            await ctx.send(f'{member.mention}, the ability to check other people\'s stats has been disabled.')
            # user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", ctx.message.mentions[0].id)
            # if user_info != None:
            #     embed = discord.Embed(title=f'{ctx.message.mentions[0].display_name}\'s Stats')
            #     embed.add_field(name="Total Practice Time", value=f'Your total time practiced is: {int(user_info["total_practice"] / 60)} hours and {user_info["total_practice"] % 60} minutes.', inline=False)
            #     embed.set_footer(text="If you believe there is a mistake, please contact @Omar#4304. This message deletes after 20 seconds.")
            #     await ctx.send(embed=embed, delete_after = 20.0)
            # else:
            #     await ctx.send(f'There is no data on {ctx.message.mentions[0].display_name}!')
        else:
            user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", member.id)
            if user_info != None:
                channel = await member.create_dm()
                embed = discord.Embed(title=f'Your practice stats')
                embed.add_field(name="Total Practice Time", value=f'Your total time practiced is: {int(user_info["total_practice"] / 60)} hours and {user_info["total_practice"] % 60} minutes.', inline=False)
                embed.set_footer(text="If you believe there is a mistake, please contact @Omar#4304.")
                await channel.send(embed=embed)
                await ctx.send(f'{member.mention}, Pratiser slid into your dm\'s!')
            else:
                await channel.send(f'We don\'t have any data on you!')
                await ctx.send(f'{member.mention}, Pratiser slid into your dm\'s!')

    @commands.command(pass_context=True)
    async def stats_silent(self, ctx, *, user_id : int = 0):
        member = ctx.author
        await ctx.send(f'{member.mention}, this command has been disabled.')
        # stats_member = await ctx.guild.fetch_member(user_id)
        # if stats_member != None:
        #     user_info = await self.bot.pg_conn.fetchrow("SELECT * FROM user_data WHERE member_id = $1", user_id)
        #     if user_info != None:
        #         embed = discord.Embed(title=f'{stats_member.display_name}\'s Stats')
        #         embed.add_field(name="Total Practice Time", value=f'Your total time practiced is: {int(user_info["total_practice"] / 60)} hours and {user_info["total_practice"] % 60} minutes.', inline=False)
        #         embed.set_footer(text="If you believe there is a mistake, please contact @Omar#4304. This message deletes after 20 seconds.")
        #         await ctx.send(embed=embed, delete_after = 20.0)
        #     else:
        #         await ctx.send(f'There is no data on {stats_member.display_name}!')
        # else:
        #     await ctx.send(f'{member.mention}, please include a user id!')

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

def setup(bot):
    bot.add_cog(Practice(bot))
