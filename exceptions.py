class RSVPException(Exception):
    pass

class UserCanceled(RSVPException):
    pass

class BadArgument(RSVPException):
    pass

class NoPermission(RSVPException):
    pass

class InvalidTz(RSVPException):
    pass

class InvalidTime(RSVPException):
    pass

class InvalidDOW(RSVPException):
    pass

class NotFound(RSVPException):
    pass
