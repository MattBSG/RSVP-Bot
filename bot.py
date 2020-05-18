import logging
import sys
import pytz

from discord.ext import commands

import constants

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

BOT = commands.Bot(command_prefix=constants.DISCORD_PREFIX)

class RSVPBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ready = False # Prevent ready calling twice

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            logging.info('[RSVP Bot] Now Ready')
            self.bot.load_extension('modules.main')

            self.ready = True

try:
    BOT.add_cog(RSVPBot(BOT))
    BOT.run(constants.DISCORD_TOKEN)

except KeyboardInterrupt:
    logging.info(['[RSVP Bot] Keyboard interrupt detected, shutting down'])
