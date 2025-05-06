"""Tests for the Bib model in the Alma API client."""

import pytest
from pydantic import ValidationError
# noinspection PyUnresolvedReferences
from datetime import datetime, timezone, date
from alma_api_client.models.bib import Bib, CodeDesc

MINIMAL_BIB_DATA = {"mms_id": "991234567890123"}

VALID_RECORD_DATA = {
    "leader": "00000cam a2200000 i 4500",
    "controlfield": [{"#text": "12345", "@tag": "001"}],
    "datafield": [
        {"@tag": "245", "subfield": [{"#text": "Test Title", "@code": "a"}]},
        {"@tag": "100", "subfield": [{"#text": "Test Author", "@code": "a"}]},
    ]
}

FULL_BIB_DATA = {
    "mms_id": "991234567890987",
    "title": "Comprehensive Test Title",
    "author": "Author, Test A.",
    "isbn": "978-3-16-148410-0",
    "issn": "1234-5678",
    "network_number": ["(OCoLC)12345678"],
    "place_of_publication": "Testville",
    "date_of_publication": "2024",
    "publisher_const": "Test Publisher",
    "link": "https://example.com/almaws/v1/bibs/991234567890987",
    "suppress_from_publishing": "false",
    "suppress_from_external_search": "True",
    "sync_with_oclc": "SYNC",
    "sync_with_libraries_australia": "NONE",
    "originating_system": "ImportSys",
    "originating_system_id": "imp-999",
    "cataloging_level": {"value": "04", "desc": "Minimal level"},
    "brief_level": {"value": "01", "desc": "Brief level 01"},
    "record_format": "marc21",
    "record": VALID_RECORD_DATA,
    "creation_date": "2023-01-10Z",
    "created_by": "import_user",
    "last_modified_date": "2024-05-02T13:20:00+00:00",
    "last_modified_by": "system_update",
}


def test_codedesc_success_full():
    """Test CodeDesc with both value and description."""
    data = {"value": "VAL", "desc": "Description"}
    cd = CodeDesc(**data)
    assert cd.value == "VAL"
    assert cd.desc == "Description"


def test_codedesc_success_value_only():
    """Test CodeDesc with only value."""
    data = {"value": "VAL"}
    cd = CodeDesc(**data)
    assert cd.value == "VAL"
    assert cd.desc is None


def test_codedesc_success_desc_only():
    """Test CodeDesc with only description."""
    data = {"desc": "Description"}
    cd = CodeDesc(**data)
    assert cd.value is None
    assert cd.desc == "Description"


def test_codedesc_success_empty():
    """Test CodeDesc with no data."""
    data = {}
    cd = CodeDesc(**data)
    assert cd.value is None
    assert cd.desc is None


def test_bib_success_minimal():
    """Test Bib instantiation with only the required mms_id."""
    bib = Bib(**MINIMAL_BIB_DATA)
    assert bib.mms_id == "991234567890123"
    assert bib.title is None
    assert bib.author is None
    assert bib.isbn is None
    assert bib.creation_date is None
    assert bib.last_modified_date is None
    assert bib.suppress_from_publishing is None
    assert bib.record_data is None
    assert bib.cataloging_level is None


def test_bib_success_full():
    """Test Bib instantiation with full, valid data, including alias and nested models."""
    bib = Bib(**FULL_BIB_DATA)
    assert bib.mms_id == "991234567890987"
    assert bib.title == "Comprehensive Test Title"
    assert bib.author == "Author, Test A."
    assert bib.isbn == "978-3-16-148410-0"
    assert bib.issn == "1234-5678"
    assert bib.network_number == ["(OCoLC)12345678"]
    assert bib.place_of_publication == "Testville"
    assert bib.date_of_publication == "2024"
    assert bib.publisher_const == "Test Publisher"
    assert bib.link == "https://example.com/almaws/v1/bibs/991234567890987"
    assert bib.suppress_from_publishing is False
    assert bib.suppress_from_external_search is True
    assert bib.sync_with_oclc == "SYNC"
    assert bib.originating_system == "ImportSys"
    assert bib.originating_system_id == "imp-999"
    assert isinstance(bib.cataloging_level, CodeDesc)
    assert bib.cataloging_level.value == "04"
    assert bib.cataloging_level.desc == "Minimal level"
    assert isinstance(bib.brief_level, CodeDesc)
    assert bib.brief_level.value == "01"
    assert bib.record_format == "marc21"
    assert bib.record_data == VALID_RECORD_DATA
    assert isinstance(bib.creation_date, datetime)
    assert bib.creation_date == datetime(2023, 1, 10, tzinfo=timezone.utc)
    assert bib.created_by == "import_user"
    assert isinstance(bib.last_modified_date, datetime)
    assert bib.last_modified_date == datetime(2024, 5, 2, 13, 20, tzinfo=timezone.utc)
    assert bib.last_modified_by == "system_update"


def test_bib_missing_required():
    """Test ValidationError when required 'mms_id' is missing."""
    invalid_data = FULL_BIB_DATA.copy()
    del invalid_data["mms_id"]
    with pytest.raises(ValidationError) as exc_info:
        Bib(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('mms_id',)


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse datetime string:")
def test_bib_date_validation():
    """Test date string validation and parsing for date fields."""
    bib1 = Bib(mms_id="1", creation_date="2024-01-15Z")
    assert bib1.creation_date == datetime(2024, 1, 15, tzinfo=timezone.utc)
    bib2 = Bib(mms_id="2", last_modified_date="2024-02-10T15:30:45+00:00")
    assert bib2.last_modified_date == datetime(2024, 2, 10, 15, 30, 45, tzinfo=timezone.utc)
    bib3 = Bib(mms_id="3", creation_date=None)
    assert bib3.creation_date is None
    dt_obj = datetime.now(timezone.utc)
    bib4 = Bib(mms_id="4", creation_date=dt_obj)
    assert bib4.creation_date == dt_obj

    with pytest.raises(ValidationError) as exc_info_inv_fmt:
        Bib(mms_id="5", creation_date="15/01/2024")
    assert exc_info_inv_fmt.value.errors(include_context=False)[0]['loc'] == ('creation_date',)

    with pytest.raises(ValidationError) as exc_info_inv_str:
        Bib(mms_id="6", last_modified_date="not-a-date")
    assert exc_info_inv_str.value.errors(include_context=False)[0]['loc'] == ('last_modified_date',)


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse boolean value:")
def test_bib_bool_validation():
    """Test boolean string validation and parsing."""
    bib1 = Bib(mms_id="1", suppress_from_publishing="true")
    assert bib1.suppress_from_publishing is True
    bib2 = Bib(mms_id="2", suppress_from_publishing="False")
    assert bib2.suppress_from_publishing is False
    bib3 = Bib(mms_id="3", suppress_from_publishing=None)
    assert bib3.suppress_from_publishing is None
    bib4 = Bib(mms_id="4", suppress_from_publishing=True)
    assert bib4.suppress_from_publishing is True

    with pytest.raises(ValidationError) as exc_info_inv_str:
        Bib(mms_id="5", suppress_from_publishing="maybe")
    errors_str = exc_info_inv_str.value.errors(include_context=False)
    assert len(errors_str) == 1
    assert errors_str[0]['loc'] == ('suppress_from_publishing',)
    assert errors_str[0]['type'] == 'bool_parsing'

    with pytest.raises(ValidationError) as exc_info_inv_type:
        Bib(mms_id="6", suppress_from_publishing=123)
    errors_type = exc_info_inv_type.value.errors(include_context=False)
    assert len(errors_type) == 1
    assert errors_type[0]['loc'] == ('suppress_from_publishing',)
    assert errors_type[0]['type'] == 'bool_parsing'


# noinspection PyTypeChecker
def test_bib_alias_record():
    """Test that the 'record' alias maps correctly to 'record_data'."""
    data = MINIMAL_BIB_DATA.copy()
    data["record"] = VALID_RECORD_DATA
    bib = Bib(**data)
    assert bib.record_data == VALID_RECORD_DATA


# noinspection PyTypeChecker
def test_bib_nested_codedesc():
    """Test handling of nested CodeDesc models."""
    data1 = MINIMAL_BIB_DATA.copy()
    data1["cataloging_level"] = {"value": "LEADER", "desc": "Leader Defined"}
    bib1 = Bib(**data1)
    assert isinstance(bib1.cataloging_level, CodeDesc)
    assert bib1.cataloging_level.value == "LEADER"
    assert bib1.cataloging_level.desc == "Leader Defined"

    data2 = MINIMAL_BIB_DATA.copy()
    data2["cataloging_level"] = None
    bib2 = Bib(**data2)
    assert bib2.cataloging_level is None

    data3 = MINIMAL_BIB_DATA.copy()
    data3["cataloging_level"] = "not-a-dict"
    with pytest.raises(ValidationError) as exc_info:
        Bib(**data3)
    assert exc_info.value.errors(include_context=False)[0]['loc'] == ('cataloging_level',)
    assert 'model_type' in exc_info.value.errors(include_context=False)[0]['type']


# noinspection PyTypeChecker
def test_bib_incorrect_type_basic():
    """Test ValidationError for incorrect basic types (e.g., mms_id)."""
    invalid_data = MINIMAL_BIB_DATA.copy()
    invalid_data["mms_id"] = 12345
    with pytest.raises(ValidationError) as exc_info:
        Bib(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'string_type'
    assert errors[0]['loc'] == ('mms_id',)
