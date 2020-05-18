import asyncio
import logging

import motor.motor_asyncio
import pendulum
import discord
from discord.ext import commands

import constants
import exceptions

mclient = motor.motor_asyncio.AsyncIOMotorClient(constants.MONGO_URI)

class Main(commands.Cog, name='RSVP Bot'):
    def __init__(self, bot):
        self.bot = bot
        self.READY = False

    async def msg_wait(self, ctx, values: list, _int=False, _list=False, content=None, embed=None, timeout=60.0):
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content # Is same author, channel, and has content

        if content: content += ' Reply `cancel` to cancel this action'
        channelMsg = await ctx.send(content, embed=embed)

        while True:
            try:
                try:
                    message = await self.bot.wait_for('message', timeout=timeout, check=check)

                except asyncio.TimeoutError:
                    await channelMsg.edit(content=f'{ctx.author.mention} The action timed out because of inactivity. Run the command again to try again')
                    raise exceptions.UserCanceled

                if message.content.strip() == 'cancel':
                    await ctx.send('Action canceled. Run the command again to try again')
                    raise exceptions.UserCanceled

                if _int:
                    msg_content = message.content.strip()
                    if _list:
                        item_list = [int(x.strip()) for x in msg_content.split(',')]
                        for item in item_list:
                            if item not in values: raise exceptions.BadArgument

                            return item_list

                    else:
                        result = int(msg_content)
                        if result not in values:
                            raise exceptions.BadArgument

                        return result

                else:
                    msg_content = message.content.strip().lower()
                    if _list:
                        item_list = [x.strip() for x in msg_content.split(',')]
                        for item in item_list:
                            if item not in values: raise exceptions.BadArgument

                        return item_list

                    else:
                        if msg_content not in values:
                            raise exceptions.BadArgument

                        return msg_content

            except (exceptions.BadArgument, ValueError):
                if content:
                    channelMsg = await ctx.send('That value doesn\'t look right, please try again. ' + content, embed=embed)

                else:
                    channelMsg = await ctx.send('That value doesn\'t look right, please try again.', embed=embed)

    async def _allowed(ctx):
        guild = await db.find_one({'_id': str(ctx.guild.id)})
        if not guild:
            # Guild not setup, command not allowed
            return False

        for role in ctx.author.roles:
            if str(role.id) in guild['access_roles']:
                return True

        return False

    @commands.command(name='setup')
    async def _setup(self, ctx):
        db = mclient.rsvpbot.config

        app_info = await self.bot.application_info()
        if ctx.author.id not in [app_info.owner.id, ctx.guild.owner.id]:
            return await ctx.send(f'{ctx.author.mention} You must be the owner of this server or bot to use this command')

        if await db.find_one({'_id': str(ctx.guild.id)}):
            return await ctx.send(f'{ctx.author.mention} This server has already been setup!')

        try:
            rsvp_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Hi, I\'m RSVP Bot. Let\'s get your server setup to use raid rsvp features. First off, what channel would you like RSVP signups in? Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')

            # Confirm role is handy and get role(s)
            await self.msg_wait(ctx, ['confirm'], content=f'Lets get some roles that will have admin priviledges; you can specify just one or as many as you would like. Once you have the roles created please gather their IDs. Let me know once you have them by replying "confirm".', timeout=180.0)
            rsvp_admins = await self.msg_wait(ctx, [x.id for x in ctx.guild.roles], _int=True, _list=True, content=f'Awesome. Please send the IDs of all roles that should have admin priviledges. This can be just one ID, or a comma seperated list (i.e. id1, id2, id3).', timeout=120.0)

            await mclient.rsvpbot.config.insert_one({
                '_id': str(ctx.guild.id),
                'channel': str(rsvp_channel),
                'access_roles': [rsvp_admins] if isinstance(rsvp_admins, int) else [str(x) for x in rsvp_admins]
            })
            return await ctx.send(f'All set! Your guild has been setup. Use the `{ctx.prefix}help` command for a list of commands')

        except exceptions.UserCanceled:
            return

        except discord.Forbidden:
            logging.error(f'[RSVP Bot] Unable to respond to setup command. Guild ({ctx.guild}) | Channel ({ctx.channel}), aborted')
            return

    @commands.group(name='rsvp', invoke_without_command=True)
    @commands.check(_allowed)
    async def _rsvp(self, ctx, day, time, tz, *, desc):
        """
        Creates a new RSVP reservation.
        Example usage:
            rsvp friday 10pm eastern Join us for a casual late night raid
            rsvp tuesday 1:15am America/New_York Who said early morning was too early?
        """
        return

    @_rsvp.command(name='alias')
    async def _rsvp_alias(self, mode, member: discord.Member, newname):
        pass

    @_rsvp.command(name='invite-msg')
    async def _rsvp_invite_msg(self, ctx, *, content):
        pass

    @_rsvp.command(name='cancel')
    async def _rsvp_cancel(self, ctx, message):
        pass

def setup(bot):
    bot.add_cog(Main(bot))
    logging.info('[Extension] Main module loaded')

def teardown(bot):
    bot.remove_cog('Main')
    logging.info('[Extension] Main module unloaded')
