"""Exceptions raised for problems the user can fix.

The CLI catches :class:`SpendrError` and prints the message instead of a traceback.
"""


class SpendrError(Exception):
    """Base class for all expected, user-facing errors."""


class NotFoundError(SpendrError):
    """A requested record does not exist."""


class DuplicateError(SpendrError):
    """A record with the same unique key already exists."""


class CategoryInUseError(SpendrError):
    """A category cannot be removed because expenses still reference it."""


class ConfigError(SpendrError):
    """The config file is unreadable or holds an invalid value."""


class DatabaseError(SpendrError):
    """The database file cannot be opened or is from an incompatible version."""
