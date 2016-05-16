class NoSessionError(Exception):
    """Raised when a model from :mod:`.models` wants to ``create``/``update``
    but it doesn't have an :class:`atomx.Atomx` session yet.
    """
    pass

class InvalidCredentials(Exception):
    """Raised when trying to login with the wrong e-mail or password."""
    pass

class APIError(Exception):
    """Raised when the atomx api returns an error that is not caught otherwise."""
    pass

class MissingArgumentError(Exception):
    """Raised when argument is missing."""
    pass

class ModelNotFoundError(Exception):
    """Raised when trying to (re-)load a model that is not in the api."""
    pass

class NoPandasInstalledError(Exception):
    """Raised when trying to access ``report.pandas`` without :mod:`pandas` installed."""
    pass
