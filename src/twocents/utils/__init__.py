from datetime import datetime


def parse_datetime(date_str: str) -> datetime:
    """Parse a datetime string and return a datetime object.

    The string must be in the format 'YYYY-MM-DD'.
    If the string is not in the correct format, a ValueError will be raised.

    Args:
        date_str (str): The datetime string to parse.

    Returns:
        datetime: A datetime object representing the parsed date.

    Raises:
        ValueError: If the input string is not in the correct format.

    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected format: 'YYYY-MM-DD'"
        ) from e


def safe_parse_datetime(date_str: str | None) -> datetime | None:
    """Safely parse a datetime string and return a datetime object.

    The string must be in the format 'YYYY-MM-DD'.
    If the string is None, None will be returned.

    Args:
        date_str (str | None): The datetime string to parse.

    Returns:
        datetime | None: A datetime object representing the parsed date, or None if the input is None.
    """
    if date_str is None:
        return None

    return parse_datetime(date_str)
