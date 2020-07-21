import discord
from discord.ext import commands
import datetime

room_ids = {}
with open('rooms.json') as json_file:
    room_ids = json.load(json_file)["rooms"]

class Practice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_permissions(self, member, before_channel_id, after_channel_id):
        """Documentation for update_permissions

        Args: member, channel_id
        :param member: a discord.py member object
        :param channel_id: an integer representation of the channel id
        :param status: A boolean describing the movement of the user. True for joining the channel.
        
        :returns: 
        :raises keyError: 
        """
        if rooms_ids[str(channel_id)]["practicing"] != member:
            if after_channel_id:
                await member.edit(mute=True)
            elif before_channel_id:
                await member.edit(mute=False)
        elif rooms_ids[str(channel_id)]["practicing"] == member:
            await member.edit(mute=False)
                
    @commands.Cog.listener()
    async def on_voice_status_update(self, member, before, after):
        if before.channel is None and after.channel is not None: # User is joining a channel
            if after.channel.id in list(room_ids.keys()):
                if room_ids[str(after.channel.id)]["practicing"] == 0: # No one is practicing yet
                    room_ids[after.channel.id]["practicing"] = member
                    await update_permissions(self, member, before.channel.id, after.channel.id)
                else: # Someone is practicing
                    await update_permissions(self, member, before.channel.id, after.channel.id)

        elif after.channel is None and before.channel is not None: # User is leaving a channel
            if before.channel.id in list(room_ids.keys())
                if rooms_ids[str(before.channel.id)]["practicing"] == member: # Person leaving the channel is the person practicing
                    room_ids[before.channel.id]["practicing"] = 0
                    await update_permissions(self, member, before.channel.id, after.channel.id)

                    if room_ids[str(before.channel.id)]["started_time"] != 0: # They started a practice session
                        duration = (datetime.datetime.now() - room_ids[str(before.channel.id)]["started_time"]).total_seconds()
                        duration = (int(duration / 3600), (duration % 3600)/60)
                else: # Person leaving the channel is not the person practicing
                    await update_permissions(self, member, before.channel.id, after.channel.id)
    
    @commands.command(pass_context=True)
    async def practice(self, ctx, member : discord.Member):
        """Start a practice session."""
        member = member or ctx.author
        if member.voice.channel.id in list(room_ids.keys()):
            if room_ids[str(member.voice.channel.id)]["practicing"] == member and room_ids[str(member.voice.channel.id)]["started_time"] == 0:
                await room_ids[str(member.voice.channel.id)]["started_time"] = datetime.datetime.now()
                await ctx.send(f'{member.mention}, [X] You are now practicing.')
            else:
                await ctx.send(f'{member.mention}, [ ] Practice session not started. You may already be practicing or someone else may be practicing!')
        else:
            await ctx.send(f'{member.mention}, You must be in one of the practice room voice channels to use this command!')
                

    @commands.command(pass_context=True)
    async def stop(self, ctx, member : discord.Member):
        """Stop a practice session."""
        member = member or ctx.author
        if member.voice.channel.id in list(room_ids.keys()):
            if room_ids[str(member.voice.channel.id)]["practicing"] == member and room_ids[str(member.voice.channel.id)]["started_time"] != 0:
                duration = (datetime.datetime.now() - room_ids[str(before.channel.id)]["started_time"]).total_seconds()
                duration = (int(duration / 3600), (duration % 3600)/60)
                await ctx.send(f'{member.mention}, [ ] You\'re no longer practicing.\nThe user who was practicing has left or does not want to practice anymore. The first person to say "$practice" will be able to practice in this channel.\nThe user practiced for {duration[0]} hours and {duration[1]} minutes')
            else:
                await ctx.send(f'{member.mention}, [ ] No practice session currently exists. You may not yet be practicing or someone else may be practicing!')
        else:
            await ctx.send(f'{member.mention}, You must be in one of the practice room voice channels to use this command!')
        

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
    bot.add_cog(Members(bot))
