"""Exceptions raised by the twocents library."""


class TwocentsError(Exception):
    """Base class for every error raised by twocents."""


class APIError(TwocentsError):
    """The Banca d'Italia API could not be reached or rejected the request.

    Attributes:
        status_code: HTTP status code, or ``None`` if no response was received
            (e.g. connection error or timeout).
        message: Error detail, usually the plain-text body sent by the API.
    """

    def __init__(self, message: str, status_code: int | None = None):
        """Init APIError.

        Args:
            message (str): Error detail.
            status_code (int | None): HTTP status code, if any.
        """
        self.message = message
        self.status_code = status_code
        prefix = f"HTTP {status_code}: " if status_code is not None else ""
        super().__init__(f"{prefix}{message}")


class InvalidDateRangeError(TwocentsError, ValueError):
    """The start date of a range is after its end date."""
