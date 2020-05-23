import asyncio
import logging

import motor.motor_asyncio
import pendulum
import discord
from discord.ext import commands

import constants
import exceptions
from modules import utility

mclient = motor.motor_asyncio.AsyncIOMotorClient(constants.MONGO_URI)

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
        guild = await mclient.rsvpbot.config.find_one({'_id': ctx.guild.id})
        if not guild:
            # Guild not setup, command not allowed
            return False

        for role in ctx.author.roles:
            if role.id in guild['access_roles']:
                return True

        return False

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

        setup = await db.find_one({'_id': ctx.guild.id})

        try:
            rsvp_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Hi, I\'m RSVP Bot. Let\'s get your server setup to use raid rsvp features. First off, what channel would you like RSVP signups in? Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')
            info_channel = await self.msg_wait(ctx, [x.id for x in ctx.guild.channels], _int=True, content=f'Thanks. Now, what channel can users find more information about raids? This can be anything such as a rules, info or faq channel). Please send the channel ID (i.e. {ctx.guild.channels[0].id}).')
            # Confirm role is handy and get role(s)
            await self.msg_wait(ctx, ['confirm'], content=f'Lets get some roles that will have admin priviledges; you can specify just one or as many as you would like. Once you have the roles created please gather their IDs. Let me know once you have them by replying "confirm".', timeout=180.0)
            rsvp_admins = await self.msg_wait(ctx, [x.id for x in ctx.guild.roles], _int=True, _list=True, content=f'Awesome. Please send the IDs of all roles that should have admin priviledges. This can be just one ID, or a comma seperated list (i.e. id1, id2, id3).', timeout=120.0)

            if setup:
                await mclient.rsvpbot.config.insert_one({
                    '_id': ctx.guild.id,
                    'rsvp_channel': rsvp_channel,
                    'info_channel': info_channel,
                    'access_roles': [rsvp_admins] if isinstance(rsvp_admins, int) else rsvp_admins
                })

            else:
                await mclient.rsvpbot.config.update_one({'_id': ctx.guild.id}, {
                    '_id': ctx.guild.id,
                    'rsvp_channel': rsvp_channel,
                    'info_channel': info_channel,
                    'access_roles': [rsvp_admins] if isinstance(rsvp_admins, int) else rsvp_admins
                })

            return await ctx.send(f'All set! Your guild has been setup. Use the `{ctx.prefix}help` command for a list of commands')

        except exceptions.UserCanceled:
            return

        except discord.Forbidden:
            logging.error(f'[RSVP Bot] Unable to respond to setup command. Guild ({ctx.guild}) | Channel ({ctx.channel}), aborted')
            return

    @commands.group(name='rsvp', invoke_without_command=True)
    @commands.check(_allowed)
    async def _rsvp(self, ctx, day, time, timezone, *, description):
        """
        Creates a new RSVP reservation.
        Example usage:
            rsvp friday 10pm eastern Join us for a casual late night raid
            rsvp tuesday 1:15am America/New_York Who said early morning was too early?
        """
        config = await mclient.rsvpbot.config.find_one({'_id': ctx.guild.id})

        time_to, rsvp_message = await utility._create_reservation(self.bot, ctx, day, time, timezone, description)

        await ctx.send(f'Success! Event created starting {time_to}')
        for emoji in self.REACT_EMOJI:
            await rsvp_message.add_reaction(emoji)

    @_rsvp.command(name='alias')
    @commands.check(_allowed)
    async def _rsvp_alias(self, ctx, mode, member: discord.Member, alias):
        mode = mode.lower()
        if mode not in ['set', 'clear']:
            # Invalid mode
            await ctx.send(f'{ctx.author.mention} :x: Provided mode "{mode}" is not valid. Must be either "set" or "clear"')

        new_alias = alias if mode == 'set' else None
        await mclient.rsvpbot.users.update_one({'_id': member.id}, {
            '$set': {
                'alias': alias
            }
        }, upsert=True)

        text_mode = mode if new_alias else 'cancelled'
        await ctx.send(f'{ctx.author.mention} :white_check_mark: Success! Alias for {member} has been set to `{alias}`')

    @_rsvp.command(name='invite-msg')
    async def _rsvp_invite_msg(self, ctx, *, content):
        pass

    @_rsvp.command(name='cancel')
    async def _rsvp_cancel(self, ctx, message):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, payload.member)

        db = mclient.rsvpbot.reservations
        user_db = mclient.rsvpbot.users
        rsvp_msg = await db.find_one({'_id': payload.message_id})
        if not rsvp_msg:
            return

        if payload.emoji.is_unicode_emoji():
            emoji = payload.emoji.name

        else:
            emoji = '<'
            if payload.emoji.animated: emoji += 'a'
            emoji += f':{payload.emoji.name}:{payload.emoji.id}>'

        if emoji not in self.REACT_EMOJI: return
        print(self.EMOJI_MAPPING[emoji])
        if emoji in [constants.EMOJI_DPS, constants.EMOJI_HEALER, constants.EMOJI_TANK]:
            for participant in rsvp_msg['participants']:
                if participant['user'] != payload.user_id: continue
                await db.update_one({'_id': payload.message_id}, {
                    '$pull': {
                        'participants': {
                            'user': payload.user_id
                        }
                    }})
                await db.update_one({'_id': payload.message_id}, {
                    '$push': {
                        'participants': {
                            'user': payload.user_id,
                            'alias': participant['alias'],
                            'role': self.EMOJI_MAPPING[emoji],
                            'status': participant['status']
                        }
                    }
                })

                return await utility._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

            user_doc = await user_db.find_one({'_id': payload.user_id})
            alias = None if not user_doc else user_doc['alias']
            await db.update_one({'_id': payload.message_id}, {
                '$push': {
                    'participants': {
                        'user': payload.user_id,
                        'alias': alias,
                        'role': self.EMOJI_MAPPING[emoji],
                        'status': 'confirmed'
                    }
                }
            })
            return await utility._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

        elif emoji in [constants.EMOJI_LATE, constants.EMOJI_TENTATIVE]:
            for participant in rsvp_msg['participants']:
                if participant['user'] != payload.user_id: continue

                status = 'confirmed' if self.EMOJI_MAPPING[emoji] == participant['status'] else self.EMOJI_MAPPING[emoji]

                await db.update_one({'_id': payload.message_id}, {
                    '$pull': {
                        'participants': {
                            'user': payload.user_id
                        }
                    }})
                await db.update_one({'_id': payload.message_id}, {
                    '$push': {
                        'participants': {
                            'user': payload.user_id,
                            'alias': participant['alias'],
                            'role': participant['role'],
                            'status': status
                        }
                    }
                })

            return await utility._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)

        elif emoji == constants.EMOJI_CANCEL:
            if payload.user_id not in [x['user'] for x in rsvp_msg['participants']]: return
            await db.update_one({'_id': payload.message_id}, {
                '$pull': {
                    'participants': {
                        'user': payload.user_id
                    }
                }})

            return await utility._rsvp_embed(self.bot, payload.guild_id, rsvp=payload.message_id)


    @commands.Cog.listener()
    async def on_reaction_remove(reaction, user):
        pass

def setup(bot):
    bot.add_cog(Main(bot))
    logging.info('[Extension] Main module loaded')

def teardown(bot):
    bot.remove_cog('Main')
    logging.info('[Extension] Main module unloaded')
