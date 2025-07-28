"""Tests for utility functions in alma_api_client.models.utils module."""

import pytest
import warnings
from datetime import datetime, date, timezone, timedelta

from wrlc_alma_api_client.models.utils import parse_datetime_optional, parse_date_optional, parse_boolean_optional


@pytest.mark.parametrize(
    "input_val, expected_output",
    [
        ("2024-05-02Z", datetime(2024, 5, 2, tzinfo=timezone.utc)),
        ("2024-05-02T10:30:00Z", datetime(2024, 5, 2, 10, 30, tzinfo=timezone.utc)),
        ("2024-05-02T15:45:30+00:00", datetime(2024, 5, 2, 15, 45, 30, tzinfo=timezone.utc)),
        ("2024-05-02T12:00:00-05:00", datetime(2024, 5, 2, 12, tzinfo=timezone(timedelta(hours=-5)))),
        ("2024-05-02T10:30:00", datetime(2024, 5, 2, 10, 30)),
        # None input
        (None, None),
    ],
    ids=[
        "zulu_date_only",
        "zulu_datetime",
        "utc_offset_zero",
        "neg_offset",
        "naive_datetime",
        "none_input",
    ]
)
def test_parse_datetime_valid(input_val, expected_output):
    """Test parse_datetime_optional with various valid inputs."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = parse_datetime_optional(input_val)
    assert len(w) == 0
    assert result == expected_output
    if expected_output is not None:
        assert isinstance(result, datetime)
        assert (result.tzinfo is not None) == (expected_output.tzinfo is not None)
    else:
        assert result is None


# noinspection PyTypeChecker
def test_parse_datetime_input_already_datetime():
    """Test parse_datetime_optional when input is already a datetime object."""
    now = datetime.now(timezone.utc)
    assert parse_datetime_optional(now) is now


@pytest.mark.parametrize(
    "invalid_input",
    [
        "02/05/2024",
        "not-a-datetime",
        "",
    ],
    ids=["dmy_format", "gibberish", "empty_string"]
)
@pytest.mark.filterwarnings("ignore:Could not parse datetime string:")
def test_parse_datetime_invalid_returns_original_and_warns(invalid_input):
    """Test parse_datetime_optional returns original value and warns on invalid string input."""
    with pytest.warns(UserWarning, match="Could not parse datetime string:"):
        result = parse_datetime_optional(invalid_input)
    assert result == invalid_input


@pytest.mark.parametrize(
    "input_val, expected_output",
    [
        ("2024-05-02", date(2024, 5, 2)),
        ("2024-12-31", date(2024, 12, 31)),
        ("2024-05-02T10:30:00Z", date(2024, 5, 2)),
        ("2024-05-02 10:30:00", date(2024, 5, 2)),
        (None, None),
    ],
    ids=["valid_date", "valid_date_end_of_year", "strip_time_z", "strip_time_space", "none_input"]
)
def test_parse_date_valid(input_val, expected_output):
    """Test parse_date_optional with various valid inputs."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = parse_date_optional(input_val)
        assert len(w) == 0
    assert result == expected_output
    if expected_output is not None:
        assert isinstance(result, date)
    else:
        assert result is None


# noinspection PyTypeChecker
def test_parse_date_input_already_date():
    """Test parse_date_optional when input is already a date object."""
    today = date.today()
    assert parse_date_optional(today) is today


@pytest.mark.parametrize(
    "invalid_input",
    [
        "02/05/2024",
        "02-May-2024",
        "tomorrow",
        "",
    ],
    ids=["dmy_format", "mon_format", "gibberish", "empty_string"]
)
@pytest.mark.filterwarnings("ignore:Could not parse date string:")
def test_parse_date_invalid_returns_original_and_warns(invalid_input):
    """Test parse_date_optional returns original value and warns on invalid string input."""
    with pytest.warns(UserWarning, match="Could not parse date string:"):
        result = parse_date_optional(invalid_input)
    assert result == invalid_input


# noinspection PyTypeChecker
def test_parse_date_invalid_type_returns_original():
    """Test parse_date_optional returns original value for non-str/date types without warning."""
    invalid_input = 12345
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = parse_date_optional(invalid_input)
        assert len(w) == 0
    assert result == invalid_input


@pytest.mark.parametrize(
    "input_val, expected_output",
    [
        ("true", True), ("True", True), ("TRUE", True),
        ("t", True), ("T", True),
        ("yes", True), ("Yes", True), ("YES", True),
        ("y", True), ("Y", True),
        ("1", True),
        ("on", True), ("On", True), ("ON", True),
        (True, True),
        ("false", False), ("False", False), ("FALSE", False),
        ("f", False), ("F", False),
        ("no", False), ("No", False), ("NO", False),
        ("n", False), ("N", False),
        ("0", False),
        ("off", False), ("Off", False), ("OFF", False),
        (False, False),
        (None, None),
    ]
)
def test_parse_boolean_valid(input_val, expected_output):
    """Test parse_boolean_optional with various valid inputs."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = parse_boolean_optional(input_val)
        assert len(w) == 0
    assert result is expected_output


@pytest.mark.parametrize(
    "invalid_input",
    [
        "maybe",
        "true ",
        " false",
        "oui",
        "ja",
        "",
        "2",
        "-1",
    ],
    ids=["maybe", "trailing_space", "leading_space", "oui", "ja", "empty", "two", "neg_one"]
)
@pytest.mark.filterwarnings("ignore:Could not parse boolean value:")
def test_parse_boolean_invalid_string_returns_original_and_warns(invalid_input):
    """Test parse_boolean_optional returns original value and warns on invalid string input."""
    with pytest.warns(UserWarning, match="Could not parse boolean value:"):
        result = parse_boolean_optional(invalid_input)
    assert result == invalid_input


# noinspection PyTypeChecker
@pytest.mark.parametrize(
    "other_input",
    [
        123,
        0.0,
        [],
        {},
    ],
    ids=["int_123", "float_zero", "list", "dict"]
)
def test_parse_boolean_other_type_returns_original(other_input):
    """Test parse_boolean_optional returns original value for non-str/bool/None types without warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = parse_boolean_optional(other_input)
        assert len(w) == 0
    assert result is other_input
