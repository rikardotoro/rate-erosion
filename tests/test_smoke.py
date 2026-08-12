from rate_erosion import __version__
from rate_erosion.errors import RateErosionError, UnknownSeriesError


def test_version_is_exposed():
    assert __version__ == "0.1.0"


def test_unknown_series_error_is_a_rate_erosion_error():
    assert issubclass(UnknownSeriesError, RateErosionError)
