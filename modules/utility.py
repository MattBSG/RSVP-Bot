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

async def _create_reservation(ctx, day, time, tz, desc):
    if tz.lower() in constants.TIMEZONE_ALIASES:
        timezone = pendulum.timezone(constants.TIMEZONE_ALIASES[tz.lower()])

    else:
        try:
            timezone = pendulum.timezone(tz.lower())

        except pendulum.tz.zoneinfo.exceptions.InvalidTimezone:
            raise exceptions.InvalidTz

    current_time = pendulum.now(timezone)

    try:
        event_time = pendulum.parse(time, tz=timezone, strict=False)

    except pendulum.parsing.exceptions.ParserError:
        raise exceptions.InvalidTime

    if current_time.at(0, 0, 0) != event_time.at(0, 0, 0): # Sanitization to prevent parsing outside the day
        raise exceptions.InvalidTime

    if day.lower() not in DAY_MAPPING:
        raise exceptions.InvalidDOW

    if current_time.day_of_week == DAY_MAPPING[day.lower()] and event_time > current_time:
        # Same as today, but in future
        event_start = event_time

    else:
        # In the future or current day (but already elasped)
        event_start = event_time.next(DAYS[DAY_MAPPING[day.lower()]]).at(event_time.hour, event_time.minute)

    await mclient.insert_one({
        'author': ctx.author.id,
        'timestamp': event_start.in_tz('UTC').int_timestamp,
        'timezone': tz.lower(),
        'description': desc,
        'created_at': pendulum.now('UTC').int_timestamp
    })

    return event_start.format('MMM DD, YYYY at h:mA') + tz.lower()
