class RevolutError(Exception):
    pass


class RevolutHttpError(RevolutError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super(RevolutHttpError, self).__init__(message)


class Unauthorized(RevolutHttpError):
    """Usually a HTTP 401/Unauthorized."""

    pass


class Forbidden(RevolutHttpError):
    """Usually a HTTP 403/Access to the requested resource or action is forbidden."""

    pass


class NotFound(RevolutHttpError):
    """Usually a HTTP 404/The requested resource could not be found."""

    pass


class MethodNotAllowed(RevolutHttpError):
    """Usually a HTTP 405/You tried to access an endpoint with an invalid method."""

    pass


class NotAccaptable(RevolutHttpError):
    """Usually a HTTP 406/You requested a format that isn't JSON."""

    pass


class RequestConflict(RevolutHttpError):
    """Usually a HTTP 409/Your request conflicts with current state of a resource."""

    pass


class TooManyRequests(RevolutHttpError):
    """Usually a HTTP 429/You're sending too many requests."""

    pass


class InternalServerError(RevolutHttpError):
    """Usually a HTTP 500/Revolut had a problem with server. Try again later."""

    pass


class ServiceUnavailable(RevolutHttpError):
    """Usually a HTTP 503/Revolut are temporarily offline for maintenance. Please try again later."""

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
