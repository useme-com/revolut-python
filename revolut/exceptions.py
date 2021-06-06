class RevolutError(Exception):
    pass


class RevolutHttpError(RevolutError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super(RevolutHttpError, self).__init__(message)


class Unauthorized(RevolutHttpError):
    pass


class CounterpartyAlreadyExists(RevolutError):
    pass


class CounterpartyAddressRequired(RevolutError):
    pass


class InsufficientBalance(RevolutError):
    pass
