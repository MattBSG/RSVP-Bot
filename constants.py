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



##############################################
#              CONFIG CONSTANTS              #
#  ONLY EDIT IF YOU KNOW WHAT YOU ARE DOING  #
##############################################
MONGO_URI = 'mongodb://root:rsvpbot@db:27017/?authSource=admin'
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
INV_DAY_MAPPING = {
    0: 'sunday',
    1: 'monday',
    2: 'tuesday',
    3: 'wednesday',
    4: 'thursday',
    5: 'friday',
    6: 'saturday',
}
STATUS_MAPPING = {
    'host': EMOJI_LEADER,
    'confirmed': EMOJI_CONFIRMED,
    'tentative': EMOJI_TENTATIVE,
    'late': EMOJI_LATE
}
