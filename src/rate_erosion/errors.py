class RateErosionError(Exception):
    """Base class for all rate-erosion errors."""


class MissingColumnError(RateErosionError):
    """A required column could not be found or mapped."""


class InvalidDataError(RateErosionError):
    """A row or value failed validation."""


class InsufficientDataError(RateErosionError):
    """Not enough usable observations to analyse."""


class UnknownSeriesError(RateErosionError):
    """The requested market benchmark series is not supported."""
