class RevolutError(Exception):
    pass


class RevolutHttpError(RevolutError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super(RevolutHttpError, self).__init__(message)


class Unauthorized(RevolutHttpError):
    """Usually a HTTP 401/Unauthorized."""

    pass


class RequestDataError(RevolutError):
    """An exception that most probably originates from invalid data passed in the request."""

    pass


class CounterpartyAlreadyExists(RequestDataError):
    pass


class CounterpartyAddressRequired(RequestDataError):
    pass


class BICIBANMismatch(RequestDataError):
    pass


class InvalidPhoneNumber(RequestDataError):
    pass


class MissingFields(RequestDataError):
    pass


class TransactionError(RevolutError):
    """An exception that makes a transaction impossible to perform."""

    pass


class InsufficientBalance(TransactionError):
    pass


class NoPocketFound(TransactionError):
    pass


class CurrencyMismatch(ValueError, RevolutError):
    pass


class DestinationNotFound(ValueError, RevolutError):
    pass
