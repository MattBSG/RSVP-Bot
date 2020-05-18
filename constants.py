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
# The key (i.e. eastern) is the user passed argument
# while the value (i.e. 'America/New_York') should a TZ data.
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
