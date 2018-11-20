class RevolutError(Exception):
    pass

class RevolutHttpError(RevolutError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super(RevolutHttpError, self).__init__(message)

class CounterpartyAlreadyExists(RevolutError):
    pass
