import asyncio
import logging
import sys
import pytz

import motor.motor_asyncio
import pendulum
import discord
from discord.ext import commands
from pymongo.errors import OperationFailure

import constants
import exceptions

LOG_FORMAT = '%(levelname)s [%(asctime)s]: %(message)s'
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

logging.info('[RSVP Bot] Starting WoW RSVP Bot - Copyright (C) Matthew Cohen 2020')

# Startup checks
logging.debug('[RSVP Bot] Running pre-flight')
if not constants.DISCORD_TOKEN or constants.DISCORD_TOKEN == 'inserttokenhere':
    # Token unset or blank
    logging.fatal('[RSVP Bot] Token is invalid')
    logging.fatal('Edit your token in constants.py and run again')
    sys.exit(1)

elif not constants.DISCORD_PREFIX:
    # No prefix is present
    logging.fatal('[RSVP Bot] No prefix is provided')
    logging.fatal('Edit your prefix in constants.py and run again')
    sys.exit(1)

for x, y in constants.TIMEZONE_ALIASES.items():
    if y not in pytz.all_timezones:
        # TZ data does not appear to exist
        logging.fatal('[RSVP Bot] Timezone alias settings are invalid!')
        logging.fatal(f'Bad alias "{x}" for unknown timezone "{y}"')
        logging.fatal('Ensure this TZ data is correct. Timezones are case-sensitive')
        sys.exit(1)

mclient = motor.motor_asyncio.AsyncIOMotorClient(constants.MONGO_URI)
bot = commands.Bot(command_prefix=constants.DISCORD_PREFIX)

class RSVPBot(commands.Cog):
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

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.READY:
            self.READY = True

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
    async def _rsvp(self, ctx, day, time, tz, *, desc):
        pass

    @_rsvp.command(name='alias')
    async def _rsvp_alias(self, mode, member: discord.Member, newname):
        pass

    @_rsvp.command(name='invite-msg')
    async def _rsvp_invite_msg(self, ctx, *, content):
        pass

    @_rsvp.command(name='cancel')
    async def _rsvp_cancel(self, ctx, message):
        pass


bot.add_cog(RSVPBot(bot))
try:
    bot.run(constants.DISCORD_TOKEN)

except (KeyboardInterrupt):
    logging.info(['[RSVP Bot] Keyboard interrupt detected, shutting down'])
