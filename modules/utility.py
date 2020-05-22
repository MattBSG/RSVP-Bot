from discord import Embed, Member, Guild
import motor.motor_asyncio
import pendulum

import constants
import exceptions

mclient = motor.motor_asyncio.AsyncIOMotorClient(constants.MONGO_URI)

DAYS = {
    0: pendulum.SUNDAY,
    1: pendulum.MONDAY,
    2: pendulum.TUESDAY,
    3: pendulum.WEDNESDAY,
    4: pendulum.THURSDAY,
    5: pendulum.FRIDAY,
    6: pendulum.SATURDAY
}
DAY_MAPPING = {
    'sunday': 0,
    'monday': 1,
    'tuesday': 2,
    'wednesday': 3,
    'thursday': 4,
    'friday': 5,
    'saturday': 6,
}
STATUS_MAPPING = {
    'host': constants.EMOJI_LEADER,
    'confirmed': constants.EMOJI_CONFIRMED,
    'tentative': constants.EMOJI_TENTATIVE,
    'late': constants.EMOJI_LATE
}

def timezone_alias(tz):
    timezone = tz.lower()
    if timezone in constants.TIMEZONE_ALIASES:
        return constants.TIMEZONE_ALIASES[timezone]

    return tz

async def _create_reservation(bot, ctx, day, time, tz, desc):
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

    if day.lower() not in DAY_MAPPING:
        raise exceptions.InvalidDOW

    if current_time.day_of_week == DAY_MAPPING[day.lower()] and event_time > current_time:
        # Same as today, but in future
        event_start = event_time

    else:
        # In the future or current day (but already elasped)
        event_start = event_time.next(DAYS[DAY_MAPPING[day.lower()]]).at(event_time.hour, event_time.minute)

    rsvp_event = {
        'host': ctx.author,#.id,
        'date': event_start,
        'timezone': tz.lower(),
        'description': desc,
        'created_at': pendulum.now('UTC').int_timestamp,
        'participants': []
    }
    rsvp_message = await _rsvp_embed(bot, ctx.guild, data=rsvp_event)
    rsvp_event['_id'] = rsvp_message.id
    rsvp_event['host'] = ctx.author.id
    rsvp_event['date'] = event_start.int_timestamp

    await mclient.rsvpbot.reservations.insert_one(rsvp_event)

    return event_start.format('MMM Do, Y at h:mmA') + ' ' + tz.lower().capitalize(), rsvp_message

async def _rsvp_embed(bot, guild, rsvp=0, *, data=None):
    embed = Embed(title='New Raid Scheduled', color=0x3B6F4D)
    embed.set_footer(text='RSVP Bot © MattBSG 2020')

    if not isinstance(guild, Guild): guild = bot.get_guild(guild)
    guild_doc = await mclient.rsvpbot.config.find_one({'_id': guild.id})

    if rsvp:
        doc = await mclient.rsvpbot.reservations.find_one({'_id': rsvp})
        if not doc:
            raise exceptions.NotFound('Reservation does not exist')

        leader = guild.get_member(doc['host'])
        if not leader: # Left, or uncached. Pull from api
            leader = await bot.fetch_user(doc['host'])

        participants = []
        for x in doc['participants']:
            user = guild.get_member(x['user'])
            if not user: # Left, or uncached. Pull from api
                user = await bot.fetch_user(x['user'])

            participants.append({
                'user': user,
                'alias': x['alias'],
                'role': x['role'],
                'status': x['status']
            })

        data = {
            'date': pendulum.from_timestamp(doc['date'], tz=timezone_alias(doc['timezone'])),
            'timezone': doc['timezone'],
            'description': doc['description'],
            'host': leader,
            'participants': participants
        }

    embed.description = f'{data["description"]}\n\n:man_raising_hand: {len(data["participants"])} Players signed up\n' \
                        f':alarm_clock: Scheduled to start **{data["date"].format("MMM Do, Y at h:mmA")} {data["timezone"].capitalize()}**'

    tanks = []
    healers = []
    dps = []
    for player in data['participants']:
        user = player
        status = user['status']

        if status == 'confirmed' and data['host'].id == user['user'].id:
            status = 'host'

        if user['role'] == 'tank':
            if user['alias']:
                tanks.append(STATUS_MAPPING[status] + user['alias'])

            else:
                if isinstance(user['user'], Member):
                    name = user['user'].name if not user['user'].nick else user['user'].nick

                else:
                    name = user['user'].name

                tanks.append(STATUS_MAPPING[status] + name)

        elif user['role'] == 'healer':
            if user['alias']:
                tanks.append(STATUS_MAPPING[status] + user['alias'])

            else:
                if isinstance(user['user'], Member):
                    name = user['user'].name if not user['user'].nick else user['user'].nick

                else:
                    name = user['user'].name

                healers.append(STATUS_MAPPING[status] + name)

        else:
            if user['alias']:
                tanks.append(STATUS_MAPPING[status] + user['alias'])

            else:
                if isinstance(user['user'], Member):
                    name = user['user'].name if not user['user'].nick else user['user'].nick

                else:
                    name = user['user'].name

                dps.append(STATUS_MAPPING[status] + name)

    embed.add_field(name='Tanks', value='*No one yet*' if not tanks else '\n'.join(tanks), inline=True)
    embed.add_field(name='Healers', value='*No one yet*' if not healers else '\n'.join(healers), inline=True)
    embed.add_field(name='DPS', value='*No one yet*' if not dps else '\n'.join(dps), inline=True)
    embed.add_field(name='How to signup', value=f'To RSVP for this event please react below with the role you will ' \
    f'be playing; {constants.EMOJI_TANK}Tank, {constants.EMOJI_HEALER}Healer, or {constants.EMOJI_DPS}DPS.\n' \
    f'If you are not sure if you can make the event, react with your role as well as {constants.EMOJI_TENTATIVE}tentative. ' \
    f'Excepting to be __late__ for the event? React with your role as well as {constants.EMOJI_LATE}late.\n\n' \
    f'You may react {constants.EMOJI_CANCEL} to cancel your RSVP at any time. Should you want to unmark yourself as tentative ' \
    f'or late simply react again. More information found in <#{guild_doc["info_channel"]}>'
    )

    rsvp_channel = bot.get_channel(guild_doc['rsvp_channel'])
    if rsvp:
        message = await rsvp_channel.fetch_message(rsvp) # TODO: check if message exists first
        await message.edit(embed=embed)

    else:
        message = await rsvp_channel.send(embed=embed)

    return message
"""
{
    date: pendulum.Date,
    timezone: str,
    description: str,
    leader: discord.User,
    participants: [
        {
            user: discord.Member,
            alias: None | str,
            role: str,
            status: [tentative, late, confirmed]
        }
    ]
}
"""
