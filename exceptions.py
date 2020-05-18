class RSVPException(Exception):
    pass

class UserCanceled(RSVPException):
    pass

class BadArgument(RSVPException):
    pass

class NoPermission(RSVPException):
    pass
