import logging

import discord

import constants
import exceptions

def timezone_alias(tz):
    timezone = tz.lower()
    if timezone in constants.TIMEZONE_ALIASES:
        return constants.TIMEZONE_ALIASES[timezone]

    return tz

def field_push(field, new):
    """
    Return an updated array field with new data included. Does not take fields with duplicate entries.
    """
    newList = list(field).copy()
    newList.append(new)
    return newList
    

def field_pull(field, old, _dict=False):
    """
    Return an updated field without new data included. Does not take fields with duplicate entries.
    """
    if not _dict:
        newList = list(field).copy()
        newList.remove(old)
        return newList

    else:
        newList = field.copy()
        newList[:] = [d for d in newList if d.get(old[0]) != old[1]]
        return newList

def plural(_int):
    if 0 < _int < 2:
        return ''

    else:
        return 's'

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
