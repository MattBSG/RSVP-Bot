##############################################
#          USER EDITABLE CONSTANTS           #
# EDIT THE FOLLOWING VALUES WITH NEEDED INFO #
##############################################

# Discord information. Token is bot account login token, prefix
# is the character(s) that should be added in front of commands
# (i.e. ?command). Admin role is int of admin role
DISCORD_TOKEN = 'token'
DISCORD_PREFIX = '?'

# Set aliases for timezones. All but last line should end in a comma
# The key (i.e. eastern) is the user passed argument while the value
# (i.e. 'America/New_York') should be a TZ data. Do not use spaces or uppercase in the alias.
# Find a TZ name for a region here: http://www.timezoneconverter.com/cgi-bin/findzone.tzc
TIMEZONE_ALIASES = {
    'eastern': 'America/New_York',
    'central': 'America/Chicago',
    'mountain': 'America/Denver',
    'pacific': 'America/Los_Angeles'
}

# Emoji settings. Replace with a direct unicode emoji like 🙂 or
# a custom emoji from your server in discord's format, <:name:id>.
# You can get a custom emoji's ID or unicode character by putting a
# backslash "\" before it like so: \:happy:
# Example value: <:confirmed:713126195335790672
EMOJI_TENTATIVE = '<:tentative:712499040767574037>'
EMOJI_LATE = '<:late:712499040339886151>'
EMOJI_CANCEL = '<:cancel:712499040633487441>'
EMOJI_CONFIRMED = '<:confirmed:713126195335790672>'
EMOJI_LEADER = '<:leader:713126195322945636>'
EMOJI_TANK = '<:tank:712499040943865886>'
EMOJI_HEALER = '<:healer:712499040667041816>'
EMOJI_DPS = '<:dps:712499040528498810>'

# Low player count alert thresholds. These thresholds are the
# number of players in each class and overall that should be
# required as a minimum. If a count is lower than a set value,
# admin roles will be notified 2 hours prior to the event.
# Should be an integer, i.e. 6
TANK_COUNT = 2
HEALER_COUNT = 2
DPS_COUNT = 8
TOTAL_COUNT = 10

##############################################
#              CONFIG CONSTANTS              #
#  ONLY EDIT IF YOU KNOW WHAT YOU ARE DOING  #
##############################################
import pendulum

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
    'host': EMOJI_LEADER,
    'confirmed': EMOJI_CONFIRMED,
    'tentative': EMOJI_TENTATIVE,
    'late': EMOJI_LATE
}
