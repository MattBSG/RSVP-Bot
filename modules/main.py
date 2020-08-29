import asyncio
import logging
import re
import typing

import pendulum
import discord
from discord.ext import commands, tasks
from tinymongo import TinyMongoClient

import constants
import exceptions
from modules import utility

mclient = TinyMongoClient('tinydb')

class Background(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._rsvp_triggers.start() #pylint: disable=no-member

    def cog_unload(self):
        self._rsvp_triggers.stop() #pylint: disable=no-member

    @tasks.loop(minutes=1)
    async def _rsvp_triggers(self):
        reservations = mclient.rsvpbot.reservations.find({'active': True})
        for rsvp in reservations:
            config = mclient.rsvpbot.config.find_one({'_id': rsvp['guild']})
            start_date = pendulum.from_timestamp(rsvp['date'], tz=utility.timezone_alias(rsvp['timezone']))
            current_date = pendulum.now(utility.timezone_alias(rsvp['timezone']))

            date_diff = start_date - current_date
            human_diff = current_date.add(seconds=date_diff.seconds).diff_for_humans()
            if date_diff.seconds <= 7200 and not rsvp['admin_reminder']: # 2 hours prior, and first notification
                participant_count = len(rsvp["participants"])
                tanks = 0
                healers = 0
                dps = 0

                for user in rsvp['participants']:
                    if user['role'] == 'tank':
                        tanks += 1

                    elif user['role'] == 'healer':
                        healers += 1
                    
                    elif user['role'] == 'dps':
                        dps += 1

                if tanks < constants.TANK_COUNT or healers < constants.HEALER_COUNT or dps < constants.DPS_COUNT or participant_count < constants.TOTAL_COUNT:
                    alert_roles = []
                    for x in config['access_roles']:
                        alert_roles.append(f'<@&{x}>')

                    role_mentions = ' '.join(alert_roles)
                    admin_channel = self.bot.get_channel(config['admin_channel'])


                    try:
                        await admin_channel.send(f'{role_mentions} Raid event notification: scheduled raid {human_diff} has less members than minimum threshold for an event.\n' \
                                                 f':man_raising_hand: **{participant_count}** user{utility.plural(participant_count)} {"is" if participant_count == 1 else "are"} signed up. Of these there are ' \
                                                 f'**{tanks}** {constants.EMOJI_TANK}tank{utility.plural(tanks)}, **{healers}** {constants.EMOJI_HEALER}healer{utility.plural(healers)}, and **{dps}** {constants.EMOJI_DPS}dps.')

                    except discord.Forbidden:
                        if admin_channel:
                            logging.error(f'[RSVP Bot] Unable to send low player count alert to admins. Guild ({admin_channel.guild}) | Channel ({admin_channel.channel}), aborted')

                    mclient.rsvpbot.reservations.update_one({'_id': rsvp['_id']}, {'$set': {
                        'admin_reminder': True
                    }})

            if date_diff.seconds <= 900 and not rsvp['user_reminder']: # 15 minutes prior, and first notification
                rsvp_channel = self.bot.get_channel(config['rsvp_channel'])
                users = [f'<@!{u["user"]}>' for u in rsvp['participants']]
                await rsvp_channel.send(f':bellhop: Event starting soon! {mclient.rsvpbot.config.find_one({"_id": rsvp["guild"]})["invite_message"]}\n\n{", ".join(users)}')

                mclient.rsvpbot.reservations.update_one({'_id': rsvp['_id']}, {'$set': {
                    'user_reminder': True
                }})

            if date_diff.seconds <= 0:
                try:
                    rsvp_message = await self.bot.get_channel(rsvp['channel']).fetch_message(rsvp['_id'])

                except (discord.NotFound, discord.Forbidden, AttributeError) as e:
                    logging.error(f'[Main] Unable to edit reservation message after it has started. Error from Discord: {e}')
                    mclient.rsvpbot.reservations.update_one({'_id': rsvp['_id']}, {
                        '$set': {
                            'active': False
                        }
                    })
                    continue

                mclient.rsvpbot.reservations.update_one({'_id': rsvp['_id']}, {
                    '$set': {
                        'active': False
                    }
                })

                embed = rsvp_message.embeds[0]
                embed.color = 0x378092
                embed.title = '[Locked] ' + embed.title
                embed.remove_field(3) # How-to-signup field

                await rsvp_message.edit(embed=embed)
                await rsvp_message.clear_reactions()

class Main(commands.Cog, name='RSVP Bot'):
    def __init__(self, bot):
        self.bot = bot
        self.READY = False
        self.REACT_EMOJI = [
            constants.EMOJI_TANK,
            constants.EMOJI_HEALER,
            constants.EMOJI_DPS,
            constants.EMOJI_TENTATIVE,
            constants.EMOJI_LATE,
            constants.EMOJI_CANCEL
        ]
        self.EMOJI_MAPPING = {
            constants.EMOJI_DPS: 'dps',
            constants.EMOJI_TANK: 'tank',
            constants.EMOJI_HEALER: 'healer',
            constants.EMOJI_TENTATIVE: 'tentative',
            constants.EMOJI_LATE: 'late',
            constants.EMOJI_CANCEL: 'cancel',
            constants.EMOJI_LEADER: 'host',
            constants.EMOJI_CONFIRMED: 'confirmed'
        }
        self._recurring_event_trigger.start() #pylint: disable=no-member

    def cog_unload(self):
        self._recurring_event_trigger.stop() #pylint: disable=no-member

    @tasks.loop(seconds=10)
    async def _recurring_event_trigger(self):
        db = mclient.rsvpbot.recurring
        for rule in db.find({}):
            if pendulum.now(tz=utility.timezone_alias(rule['timezone'])).int_timestamp >= rule['next_run']: # Up for event posting
                if rule['freq'] == 'daily':
                    await self._create_reservation(day=rule['next_run'] + (60 * 60 * 24), tz=utility.timezone_alias(rule['timezone']), desc=rule['description'], recurr=rule)
                    db.update_one({'_id': rule['_id']}, {'$set': {
                        'next_run': rule['next_run'] + (60 * 60 * 24)
                    }})

                elif rule['freq'] == 'weekly':
                    await self._create_reservation(day=rule['next_run'] + (60 * 60 * 24 * 7), tz=utility.timezone_alias(rule['timezone']), desc=rule['description'], recurr=rule)
                    db.update_one({'_id': rule['_id']}, {'$set': {
                        'next_run': rule['next_run'] + (60 * 60 * 24 * 7)
                    }})

                else: # biweekly - run every 2 weeks, making a rsvp the next week
                    await self._create_reservation(day=rule['next_run'] + (60 * 60 * 24 * 7), tz=utility.timezone_alias(rule['timezone']), desc=rule['description'], recurr=rule)
                    db.update_one({'_id': rule['_id']}, {'$set': {
                        'next_run': rule['next_run'] + (60 * 60 * 24 * 14)
                    }})

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
        guild = mclient.rsvpbot.config.find_one({'_id': ctx.guild.id})

        if not guild:
            # Guild not setup, command not allowed
            return False

        for role in ctx.author.roles:
            if role.id in guild['access_roles']:
                return True

        return False

    async def _rsvp_embed(self, bot, guild, rsvp=0, *, data=None):
        embed = discord.Embed(title='Raid Signup', color=0x3B6F4D)
        embed.set_footer(text='RSVP Bot © MattBSG 2020')

        if not isinstance(guild, discord.Guild): guild = bot.get_guild(guild)
        guild_doc = mclient.rsvpbot.config.find_one({'_id': guild.id})

        if rsvp:
            doc = mclient.rsvpbot.reservations.find_one({'_id': rsvp})
            if not doc:
                raise exceptions.NotFound('Reservation does not exist')

            leader = guild.get_member(doc['host'])
            if not leader: # Left, or uncached. Pull from api
                leader = await bot.fetch_user(doc['host'])

            user_aliases = {}
            user_db = mclient.rsvpbot.users
            alias_docs = user_db.find({'_id': {'$in': [x['user'] for x in doc['participants']]}})
            for x in alias_docs:
                user_aliases[x['_id']] = x['alias']

            participants = []
            for x in doc['participants']:
                user = guild.get_member(x['user'])
                if not user: # Left, or uncached. Pull from api
                    user = await bot.fetch_user(x['user'])

                participants.append({
                    'user': user,
                    'alias': None if not user.id in user_aliases else user_aliases[user.id],
                    'role': x['role'],
                    'status': x['status']
                })

            data = {
                'date': pendulum.from_timestamp(doc['date'], tz=utility.timezone_alias(doc['timezone'])),
                'timezone': doc['timezone'],
                'description': doc['description'],
                'host': leader,
                'participants': participants
            }

        embed.description = f'{data["description"]}\n\n:man_raising_hand: {len(data["participants"])} Player{utility.plural(len(data["participants"]))} signed up\n' \
                            f':alarm_clock: Scheduled to start **{data["date"].format("MMM Do, Y at h:mmA")} {data["timezone"].capitalize()}**'
        tanks = []
        healers = []
        dps = []
        for player in data['participants']:
            user = player
            status = user['status']
            if user['alias']:
                user_alias = user['alias']

            elif isinstance(user['user'], discord.Member):
                user_alias = user['user'].name if not user['user'].nick else user['user'].nick

            else:
                user_alias = user['user'].name

            if status == 'confirmed' and data['host'].id == user['user'].id:
                status = 'host'

            if user['role'] == 'tank':
                tanks.append(constants.STATUS_MAPPING[status] + user_alias)

            elif user['role'] == 'healer':
                healers.append(constants.STATUS_MAPPING[status] + user_alias)

            else:
                dps.append(constants.STATUS_MAPPING[status] + user_alias)

        embed.add_field(name='Tanks', value='*No one yet*' if not tanks else '\n'.join(tanks), inline=True)
        embed.add_field(name='Healers', value='*No one yet*' if not healers else '\n'.join(healers), inline=True)
        embed.add_field(name='DPS', value='*No one yet*' if not dps else '\n'.join(dps), inline=True)
        embed.add_field(name='How to signup', value=f'To RSVP for this event please react below with the role you will ' \
        f'be playing; {constants.EMOJI_TANK}Tank, {constants.EMOJI_HEALER}Healer, or {constants.EMOJI_DPS}DPS.\n' \
        f'If you are not sure if you can make the event, react with your role as well as {constants.EMOJI_TENTATIVE}tentative. ' \
        f'Expecting to be __late__ for the event? React with your role as well as {constants.EMOJI_LATE}late.\n\n' \
        f'Should you want to unmark yourself as tentative or late simply react again. ' \
        f'You may react {constants.EMOJI_CANCEL} to cancel your RSVP at any time. More information found in <#{guild_doc["info_channel"]}>'
        )

        rsvp_channel = self.bot.get_channel(guild_doc['rsvp_channel'])
        if rsvp:
            try:
                message = await rsvp_channel.fetch_message(rsvp)
                await message.edit(embed=embed)

            except (discord.NotFound, discord.Forbidden):
                logging.error(f'[Main] Unable to fetch RSVP message {rsvp}, resending! Was it deleted?')
                message = await rsvp_channel.send(embed=embed)

        else:
            message = await rsvp_channel.send(embed=embed)

        return message

    async def _create_reservation(self, bot=None, ctx=None, day=None, time=None, tz=None, desc=None, recurr=None):
        if recurr:
            event_start = pendulum.from_timestamp(day, tz=tz)


        else:
            if tz.lower() in constants.TIMEZONE_ALIASES:
                timezone = pendulum.timezone(constants.TIMEZONE_ALIASES[tz.lower()])

            else:
                try:
                    timezone = pendulum.timezone(tz.lower())

                except pendulum.tz.zoneinfo.exceptions.InvalidTimezone:
                    raise exceptions.InvalidTz

            current_time = pendulum.now(timezone)

            try:
                event_time = pendulum.parse(time, tz=timezone, strict=False).on(current_time.year, current_time.month, current_time.day)

            except pendulum.parsing.exceptions.ParserError:
                raise exceptions.InvalidTime

            if day.lower() not in constants.DAY_MAPPING:
                raise exceptions.InvalidDOW

            if current_time.day_of_week == constants.DAY_MAPPING[day.lower()] and event_time > current_time:
                # Same as today, but in future
                event_start = event_time

            else:
                # In the future or current day (but already elasped)
                event_start = event_time.next(constants.DAYS[constants.DAY_MAPPING[day.lower()]]).at(event_time.hour, event_time.minute)

        rsvp_event = {
            'host': ctx.author if not recurr else recurr['host'],
            'channel': ctx.channel.id if not recurr else recurr['channel'],
            'guild': ctx.guild.id if not recurr else recurr['guild'],
            'date': event_start,
            'timezone': utility.timezone_alias(tz),
            'description': desc,
            'created_at': pendulum.now('UTC').int_timestamp,
            'participants': [],
            'admin_reminder': False,
            'user_reminder': False,
            'active': True,
            'recurring': None if not recurr else recurr['_id']
        }
        rsvp_message = await self._rsvp_embed(bot, ctx.guild if not recurr else self.bot.get_guild(recurr['guild']), data=rsvp_event)
        rsvp_event['_id'] = rsvp_message.id
        rsvp_event['host'] = ctx.author.id if not recurr else recurr['host']
        rsvp_event['date'] = event_start.int_timestamp

        mclient.rsvpbot.reservations.insert_one(rsvp_event)

        for emoji in self.REACT_EMOJI:
            await rsvp_message.add_reaction(emoji)

        return event_start.format('MMM Do, Y at h:mmA') + ' ' + tz.lower().capitalize(), rsvp_message

    @commands.command(name='setup')
    async def _setup(self, ctx):
        """
        Perform server setup with RSVP Bot.

        Can be used to setup the bot for the first time, or to change settings.
        Example usage:
            setup
        """
        db = mclient.rsvpbot.config

        app_info = await self.bot.application_info()
        if ctx.author.id not in [app_info.owner.id, ctx.guild.owner.id]:
            return await ctx.send(f'{ctx.author.mention} You must be the owner of this server or bot to use this command')

        setup = db.find_one({'_id': ctx.guild.id})

        try:
            rsvp_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Hi, I\'m RSVP Bot. Let\'s get your server setup to use raid rsvp features. First off, what channel would you like RSVP signups in? Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')
            info_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Thanks. Now, what channel can users find more information about raids? This can be anything such as a rules, info or faq channel). Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')
            admin_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Cool. Where should notifications to admins be sent? Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')
            # Confirm role is handy and get role(s)
            await self.msg_wait(ctx, ['confirm'], content=f'Lets get some roles that will have admin priviledges; you can specify just one or as many as you would like. Once you have the roles created please gather their IDs.\n\n**Let me know once you have them by replying "confirm".**', timeout=180.0)
            rsvp_admins = await self.msg_wait(ctx, [x.id for x in ctx.guild.roles], _int=True, _list=True, content=f'Awesome. Please send the IDs of all roles that should have admin priviledges. This can be just one ID, or a comma seperated list (i.e. id1, id2, id3).', timeout=120.0)

            if not setup:
                mclient.rsvpbot.config.insert_one({
                    '_id': ctx.guild.id,
                    'rsvp_channel': rsvp_channel,
                    'info_channel': info_channel,
                    'admin_channel': admin_channel,
                    'access_roles': [rsvp_admins] if isinstance(rsvp_admins, int) else rsvp_admins,
                    'invite_message': 'Raid is about to begin. Please log in for an invite and summon.'
                })

            else:
                mclient.rsvpbot.config.update_one({'_id': ctx.guild.id}, {
                    '_id': ctx.guild.id,
                    'rsvp_channel': rsvp_channel,
                    'info_channel': info_channel,
                    'admin_channel': admin_channel,
                    'access_roles': [rsvp_admins] if isinstance(rsvp_admins, int) else rsvp_admins
                })

            return await ctx.send(f'All set! Your guild has been setup. Use the `{ctx.prefix}help` command for a list of commands')

        except exceptions.UserCanceled:
            return

        except (discord.Forbidden, discord.NotFound):
            logging.error(f'[RSVP Bot] Unable to respond to setup command. Guild ({ctx.guild}) | Channel ({ctx.channel}), aborted')
            return

    @commands.group(name='rsvp', invoke_without_command=True)
    @commands.check(_allowed)
    async def _rsvp(self, ctx, day, time, timezone, *, description):
        """
        Creates a new RSVP reservation.

        Timezone is an alias set in the config or a raw timezone name (http://www.timezoneconverter.com/cgi-bin/findzone.tzc)
        Example usage:
            rsvp friday 10pm eastern Join us for a casual late night raid
            rsvp tuesday 1:15am America/New_York Who said early morning was too early?
        """
        config = mclient.rsvpbot.config.find_one({'_id': ctx.guild.id})

        time_to, rsvp_message = await self._create_reservation(self.bot, ctx, day, time, timezone, description)

        await ctx.send(f'Success! Event created starting {time_to}')

    @_rsvp.group(name='recurr', invoke_without_command=True)
    @commands.check(_allowed)
    async def _rsvp_recurr(self, ctx, reservation: typing.Union[int, str], frequency):
        """
        Set an event to recurr daily, weekly, or biweekly.

        Takes a message for an event and makes it recurr for an internal of time.
        Example usage:
            rsvp recurr 748995539026182296 daily
            rsvp recurr 748994176124977173 weekly
            rsvp recurr https://discordapp.com/channels/314857672585248768/314857672585248768/748993895131775057 biweekly
        """
        frequency = frequency.lower()
        if frequency not in ['daily', 'weekly', 'biweekly']:
            return await ctx.send(f':x: {ctx.author.mention} The provided frequency "{frequency}" is not valid. It should be either "daily", "weekly", or "biweekly"')

        db = mclient.rsvpbot.recurring
        if isinstance(reservation, int):
            rsvp = mclient.rsvpbot.reservations.find_one({'_id': reservation, 'active': True})

        else: # String
            match = re.search(r'https:\/\/\w*\.?discord(?:app)?.com\/channels\/\d+\/\d+\/(\d+)', reservation, flags=re.I)
            if not match:
                return await ctx.send(f':x: {ctx.author.mention} The reservation provided is invalid. Make sure you use a message ID or message link')

            rsvp = mclient.rsvpbot.reservations.find_one({'_id': int(match.group(1)), 'active': True})

        if not rsvp:
            return await ctx.send(f':x: {ctx.author.mention} The provided reservation is either inactive, not not valid')

        recurr = db.find_one({'description': rsvp['description']})
        if recurr:
            return await ctx.send(f':x: {ctx.author.mention} That event is already recurring {recurr["freq"]}. If you wish to change the frequency, you must stop it from recurring first. '\
                            f'See `{ctx.prefix}help rsvp recurr` for more info')

        if frequency in ['daily', 'weekly']:
            next_run = rsvp['date']

        else: # biweekly
            next_run = rsvp['date'] + (60 * 60 * 24 * 7) # 1 week delay

        doc = db.insert_one({
            'freq': frequency,
            'next_run': next_run,
            'host': rsvp['host'],
            'channel': rsvp['channel'],
            'guild': rsvp['guild'],
            'timezone': rsvp['timezone'],
            'description': rsvp['description'],
        })
        mclient.rsvpbot.reservations.update_one({'_id': rsvp['_id']}, {
            'recurring': doc.inserted_id
        })

        await ctx.send(f':white_check_mark: Success! The event will now recurr **{frequency}**')

    @_rsvp_recurr.command(name='stop')
    @commands.check(_allowed)
    async def _rsvp_recurr_stop(self, ctx, reservation: typing.Union[int, str]):
        """
        Stops an event from recurring.

        Takes a message for any reservation in the recurring series and stops it from recurring
        further. Will not cancel events in the series that currently have reservations open.
        Example usage:
            rsvp recurr stop 748993895131775057
            rsvp recurr stop https://discordapp.com/channels/314857672585248768/314857672585248768/748995539026182296
        """
        if isinstance(reservation, int):
            rsvp = mclient.rsvpbot.reservations.find_one({'_id': reservation})

        else: # String
            match = re.search(r'https:\/\/\w*\.?discord(?:app)?.com\/channels\/\d+\/\d+\/(\d+)', reservation, flags=re.I)
            if not match:
                return await ctx.send(f':x: {ctx.author.mention} The reservation provided is invalid. Make sure you use a message ID or message link')

            rsvp = mclient.rsvpbot.reservations.find_one({'_id': int(match.group(1))})

        if not rsvp:
            return await ctx.send(f':x: {ctx.author.mention} The provided message is not a reservation')

        if not rsvp['recurring']:
            return await ctx.send(f':x: {ctx.author.mention} The provided event reservation is not currently recurring')

        recurr = mclient.rsvpbot.recurring.find_one({'_id': rsvp['recurring']})
        if not recurr:
            # This would be caused by an event previously recurring, but is not currently
            return await ctx.send(f':x: {ctx.author.mention} The provided event reservation is not currently recurring')

        mclient.rsvpbot.recurring.delete_one({'_id': recurr['_id']})

        await ctx.send(f':white_check_mark: {ctx.author.mention} Success! The event is no longer recurring. Any active reservations part of this series will '\
                        'still continue to function until canceled')

    @_rsvp.command(name='alias')
    @commands.check(_allowed)
    async def _rsvp_alias(self, ctx, mode, member: discord.Member, alias=None):
        """
        Creates a reservation alias for a user.

        This will change the display name of a user to the alias in rsvp embeds
        Example usage:
            rsvp alias set @MattBSG#8888 Matt
            rsvp alias clear @MattBSG#8888
        """
        mode = mode.lower()
        if mode not in ['set', 'clear']:
            # Invalid mode
            await ctx.send(f':x: {ctx.author.mention} The provided mode "{mode}" is not valid. It should be either "set" or "clear"')

        if mode == 'set': 
            if not alias: await ctx.send(f':x: {ctx.author.mention} A name to alias this user to is required')
            new_alias = alias if mode == 'set' else None
            user_db = mclient.rsvpbot.users
            if user_db.find_one({'_id': member.id}):
                user_db.update_one({'_id': member.id}, {
                    '$set': {
                        'alias': alias
                    }
                })

            else:
                user_db.insert_one({
                    '_id': member.id,
                    'alias': alias
                })

            await ctx.send(f':white_check_mark: {ctx.author.mention}  Success! Alias for {member} has been set to `{alias}`')

        else:
            mclient.rsvpbot.users.delete_one({'_id': member.id})
            await ctx.send(f':white_check_mark: {ctx.author.mention} Success! Alias for {member} has been cleared')


    @_rsvp.command(name='message', aliases=['msg'])
    @commands.check(_allowed)
    async def _rsvp_invite_msg(self, ctx, *, content):
        """
        Sets the invitation message used.

        The invitation message is used when alerting users a raid
        is about to begin. 
        Example:
            rsvp message The raid will be starting soon, please login and join the voice channel!
        """
        mclient.rsvpbot.config.update_one({'_id': ctx.guild.id}, {
            '$set': {
                'invite_message': content
            }
        })

        await ctx.send(f':white_check_mark: {ctx.author.mention} Success! RSVP invite message set: ```\n{content}```')

    @_rsvp.command(name='cancel')
    @commands.check(_allowed)
    async def _rsvp_cancel(self, ctx, message: typing.Union[int, str]):
        """
        Cancels a reservation that is waiting for players.

        Will cancel a reservation when provided with it's message ID or link
        Example:
            rsvp cancel 748924482894430278
            rsvp cancel https://discordapp.com/channels/133055605479964672/133055605479964672/748924482894430278
        """
        if isinstance(message, int):
            messageID = message

        else: # String
            match = re.search(r'https:\/\/\w*\.?discord(?:app)?.com\/channels\/\d+\/\d+\/(\d+)', message, flags=re.I)
            if not match:
                return await ctx.send(f':x: {ctx.author.mention} The message provided is invalid. Make sure you use a message ID or message link')

            messageID = int(match.group(1))

        reservation = mclient.rsvpbot.reservations.find_one({'_id': messageID})
        if not reservation:
            return await ctx.send(f':x: {ctx.author.mention} That message is not an active RSVP')

        if not reservation['active']:
            return await ctx.send(f':x: {ctx.author.mention} That message is not an active RSVP')

        try:
            rsvp_message = await self.bot.get_channel(reservation['channel']).fetch_message(messageID)

        except (discord.NotFound, discord.Forbidden, AttributeError):
            return await ctx.send(f':x: {ctx.author.mention} That RSVP message either no longer exists or I unable to view it\'s channel')

        mclient.rsvpbot.reservations.update_one({'_id': reservation['_id']}, {
            '$set': {
                'active': False
            }
        })

        embed = rsvp_message.embeds[0]
        embed.color = 0xB84444
        embed.title = '[Canceled] ' + embed.title
        embed.remove_field(3) # How-to-signup field

        await rsvp_message.edit(embed=embed)
        await rsvp_message.clear_reactions()
        await ctx.send(f':white_check_mark: {ctx.author.mention} Success! That event has been canceled')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        db = mclient.rsvpbot.reservations
        user_db = mclient.rsvpbot.users
        rsvp_msg = db.find_one({'_id': payload.message_id})
        if not rsvp_msg:
            return

        if payload.emoji.is_unicode_emoji():
            emoji = payload.emoji.name

        else:
            emoji = '<'
            if payload.emoji.animated: emoji += 'a'
            emoji += f':{payload.emoji.name}:{payload.emoji.id}>'

        if emoji not in self.REACT_EMOJI: return
        if emoji in [constants.EMOJI_DPS, constants.EMOJI_HEALER, constants.EMOJI_TANK]:
            for participant in rsvp_msg['participants']:
                if participant['user'] != payload.user_id: continue
                db.update_one({'_id': payload.message_id}, {
                    'participants': utility.field_pull(
                        db.find_one({'_id': payload.message_id})['participants'],
                        ['user', payload.user_id],
                        _dict=True
                    )
                })
                break

            user_doc = user_db.find_one({'_id': payload.user_id})
            alias = None if not user_doc else user_doc['alias']
            db.update_one({'_id': payload.message_id}, {
                'participants': utility.field_push(
                    db.find_one({'_id': payload.message_id})['participants'],
                    {
                        'user': payload.user_id,
                        'alias': alias,
                        'role': self.EMOJI_MAPPING[emoji],
                        'status': 'confirmed'
                    }
                )
            })

            await self._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

        elif emoji in [constants.EMOJI_LATE, constants.EMOJI_TENTATIVE]:
            for participant in rsvp_msg['participants']:
                if participant['user'] != payload.user_id: continue

                status = 'confirmed' if self.EMOJI_MAPPING[emoji] == participant['status'] else self.EMOJI_MAPPING[emoji]

                db.update_one({'_id': payload.message_id}, {
                    'participants': utility.field_pull(
                        db.find_one({'_id': payload.message_id})['participants'],
                        ['user', payload.user_id],
                        _dict=True
                    )
                })

                db.update_one({'_id': payload.message_id}, {
                    'participants': utility.field_push(
                        db.find_one({'_id': payload.message_id})['participants'],
                        {
                            'user': payload.user_id,
                            'alias': participant['alias'],
                            'role': participant['role'],
                            'status': status
                        }
                    )
                })

            await self._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

        elif emoji == constants.EMOJI_CANCEL:
            if payload.user_id not in [x['user'] for x in rsvp_msg['participants']]: return
            db.update_one({'_id': payload.message_id}, {
                'participants': utility.field_pull(
                    db.find_one({'_id': payload.message_id})['participants'],
                    ['user', payload.user_id],
                    _dict=True
                )
            })

            await self._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

        await message.remove_reaction(payload.emoji, payload.member)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        cmd_str = ctx.command.full_parent_name + ' ' + ctx.command.name if ctx.command.parent else ctx.command.name
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f':x: {ctx.author.mention} You are missing one or more required arguments. See `{ctx.prefix}help {cmd_str}`')

        elif isinstance(error, commands.BadArgument) or isinstance(error, commands.BadUnionArgument):
            await ctx.send(f':x: {ctx.author.mention} One or more provided arguments are invalid. See `{ctx.prefix}help {cmd_str}`')

        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f':x: {ctx.author.mention} You do not have permission to run that command. See `{ctx.prefix}help` for commands you have access to')

def setup(bot):
    bot.add_cog(Main(bot))
    logging.info('[Extension] Main module loaded')
    bot.add_cog(Background(bot))
    logging.info('[Extension] Background task module loaded')

def teardown(bot):
    bot.remove_cog('Main')
    logging.info('[Extension] Main module unloaded')
    bot.remove_cog('Background')
    logging.info('[Extension] Background task module unloaded')
