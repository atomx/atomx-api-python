class NoSessionError(Exception):
    pass

class InvalidCredentials(Exception):
    pass

class APIError(Exception):
    pass

class ModelNotFoundError(Exception):
    pass

class ReportNotReadyError(Exception):
    pass

class NoPandasInstalledError(Exception):
    pass
