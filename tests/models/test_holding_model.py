"""Tests for the Holding models in the Alma API client."""

import pytest
from pydantic import ValidationError
# noinspection PyUnresolvedReferences
from datetime import datetime, timezone, date
from api_client.models.bib import CodeDesc
from api_client.models.holding import Holding, BibLinkData


MINIMAL_HOLDING_DATA = {"holding_id": "221111111000541"}

VALID_CODEDESC_LIBRARY = {"value": "MAIN", "desc": "Main Library"}
VALID_CODEDESC_LOCATION = {"value": "STACKS", "desc": "Main Stacks"}
VALID_CODEDESC_CN_TYPE = {"value": "0", "desc": "Library of Congress classification"}

VALID_BIB_LINK_DATA_DICT = {
    "mms_id": "998888888000541",
    "title": "Linked Bib Title",
    "author": "Linked Author",
    "isbn": "978-1-23-456789-0",
    "link": "https://example.com/almaws/v1/bibs/998888888000541"
}

VALID_RECORD_DATA_HOLDING = {
    "leader": "00000nu  a2200000un 4500",
    "controlfield": [{"#text": "221111111000541", "@tag": "001"}],
    "datafield": [
        {"@tag": "852", "subfield": [
            {"@code": "b", "#text": "MAIN"},
            {"@code": "c", "#text": "STACKS"},
            {"@code": "h", "#text": "QA76.73.P98"},
            {"@code": "i", "#text": "P98 2023"}
        ]}
    ]
}

FULL_HOLDING_DATA = {
    "holding_id": "229999999000541",
    "link": "https://example.com/almaws/v1/bibs/998888888000541/holdings/229999999000541",
    "created_by": "migration_user",
    "created_date": "2022-11-01Z",
    "last_modified_by": "circ_desk",
    "last_modified_date": "2024-04-15T09:00:00+00:00",
    "suppress_from_publishing": "false",
    "calculated_suppress_from_publishing": "false",
    "originating_system": "ILS Migration",
    "originating_system_id": "ils-h-555",
    "library": VALID_CODEDESC_LIBRARY,
    "location": VALID_CODEDESC_LOCATION,
    "call_number_type": VALID_CODEDESC_CN_TYPE,
    "call_number": "QA76.73.P98 P98 2023",
    "accession_number": "A123456",
    "copy_id": "c.1",
    "anies": VALID_RECORD_DATA_HOLDING,
    "bib_data": VALID_BIB_LINK_DATA_DICT
}



def test_biblinkdata_success_full():
    """Test BibLinkData with all fields."""
    link_data = BibLinkData(**VALID_BIB_LINK_DATA_DICT)
    assert link_data.mms_id == "998888888000541"
    assert link_data.title == "Linked Bib Title"
    assert link_data.author == "Linked Author"
    assert link_data.isbn == "978-1-23-456789-0"
    assert link_data.link == "https://example.com/almaws/v1/bibs/998888888000541"


def test_biblinkdata_success_partial():
    """Test BibLinkData with a subset of fields."""
    partial_data = {"mms_id": "9911", "title": "Partial Title"}
    link_data = BibLinkData(**partial_data)
    assert link_data.mms_id == "9911"
    assert link_data.title == "Partial Title"
    assert link_data.author is None
    assert link_data.isbn is None
    assert link_data.link is None


def test_biblinkdata_success_empty():
    """Test BibLinkData with no fields."""
    link_data = BibLinkData(**{})
    assert link_data.mms_id is None
    assert link_data.title is None


def test_holding_success_minimal():
    """Test Holding instantiation with only required holding_id."""
    holding = Holding(**MINIMAL_HOLDING_DATA)
    assert holding.holding_id == "221111111000541"
    assert holding.library is None
    assert holding.location is None
    assert holding.call_number is None
    assert holding.bib_data is None
    assert holding.record_data is None
    assert holding.created_date is None
    assert holding.suppress_from_publishing is None


def test_holding_success_full():
    """Test Holding instantiation with full valid data, including nested models and aliases."""
    holding = Holding(**FULL_HOLDING_DATA)
    assert holding.holding_id == "229999999000541"
    assert holding.link == "https://example.com/almaws/v1/bibs/998888888000541/holdings/229999999000541"
    assert holding.created_by == "migration_user"
    assert isinstance(holding.created_date, datetime)
    assert holding.created_date == datetime(2022, 11, 1, tzinfo=timezone.utc)
    assert holding.last_modified_by == "circ_desk"
    assert isinstance(holding.last_modified_date, datetime)
    assert holding.last_modified_date == datetime(2024, 4, 15, 9, tzinfo=timezone.utc)
    assert holding.suppress_from_publishing is False
    assert holding.calculated_suppress_from_publishing is False
    assert holding.originating_system == "ILS Migration"
    assert holding.originating_system_id == "ils-h-555"

    assert isinstance(holding.library, CodeDesc)
    assert holding.library.value == "MAIN"
    assert isinstance(holding.location, CodeDesc)
    assert holding.location.value == "STACKS"
    assert isinstance(holding.call_number_type, CodeDesc)
    assert holding.call_number_type.value == "0"
    assert holding.call_number == "QA76.73.P98 P98 2023"
    assert holding.accession_number == "A123456"
    assert holding.copy_id == "c.1"

    assert holding.record_data == VALID_RECORD_DATA_HOLDING
    assert isinstance(holding.bib_data, BibLinkData)
    assert holding.bib_data.mms_id == "998888888000541"
    assert holding.bib_data.title == "Linked Bib Title"


def test_holding_missing_required():
    """Test ValidationError when required 'holding_id' is missing."""
    invalid_data = FULL_HOLDING_DATA.copy()
    del invalid_data["holding_id"]
    with pytest.raises(ValidationError) as exc_info:
        Holding(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('holding_id',)


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse datetime string:")
def test_holding_date_validation():
    """Test date string validation and parsing for date fields."""
    h1 = Holding(holding_id="h1", created_date="2023-03-20Z")
    assert h1.created_date == datetime(2023, 3, 20, tzinfo=timezone.utc)
    h2 = Holding(holding_id="h2", last_modified_date=None)
    assert h2.last_modified_date is None
    dt_obj = datetime.now(timezone.utc)
    h3 = Holding(holding_id="h3", created_date=dt_obj)
    assert h3.created_date == dt_obj

    with pytest.raises(ValidationError) as exc_info_inv_fmt:
        Holding(holding_id="h4", created_date="20-03-2023")
    errors_fmt = exc_info_inv_fmt.value.errors(include_context=False)
    assert errors_fmt[0]['loc'] == ('created_date',)
    assert errors_fmt[0]['type'] == 'datetime_from_date_parsing'

    with pytest.raises(ValidationError) as exc_info_inv_str:
        Holding(holding_id="h5", last_modified_date="yesterday")
    errors_str = exc_info_inv_str.value.errors(include_context=False)
    assert errors_str[0]['loc'] == ('last_modified_date',)
    assert errors_str[0]['type'] == 'datetime_from_date_parsing'


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse boolean value:")
def test_holding_bool_validation():
    """Test boolean string validation and parsing."""
    h1 = Holding(holding_id="h1", suppress_from_publishing="false")
    assert h1.suppress_from_publishing is False
    h2 = Holding(holding_id="h2", suppress_from_publishing=True)
    assert h2.suppress_from_publishing is True
    h3 = Holding(holding_id="h3", suppress_from_publishing=None)
    assert h3.suppress_from_publishing is None
    h4 = Holding(holding_id="h4", calculated_suppress_from_publishing="true")
    assert h4.calculated_suppress_from_publishing is True

    with pytest.raises(ValidationError) as exc_info_inv_str:
        Holding(holding_id="h5", suppress_from_publishing="maybe")
    assert exc_info_inv_str.value.errors(include_context=False)[0]['loc'] == ('suppress_from_publishing',)
    assert exc_info_inv_str.value.errors(include_context=False)[0]['type'] == 'bool_parsing'

    with pytest.raises(ValidationError) as exc_info_inv_type:
        Holding(holding_id="h6", calculated_suppress_from_publishing=123)
    assert exc_info_inv_type.value.errors(include_context=False)[0]['loc'] == ('calculated_suppress_from_publishing',)
    assert exc_info_inv_type.value.errors(include_context=False)[0]['type'] == 'bool_parsing'


# noinspection PyTypeChecker
def test_holding_alias_record_data():
    """Test that the 'anies' alias maps correctly to 'record_data'."""
    data = MINIMAL_HOLDING_DATA.copy()
    data["anies"] = VALID_RECORD_DATA_HOLDING
    holding = Holding(**data)
    assert holding.record_data == VALID_RECORD_DATA_HOLDING


# noinspection PyTypeChecker
def test_holding_nested_codedesc():
    """Test handling of nested CodeDesc models for library/location."""
    data = MINIMAL_HOLDING_DATA.copy()
    data["library"] = VALID_CODEDESC_LIBRARY
    data["location"] = None
    data["call_number_type"] = {"value": "9"}
    holding = Holding(**data)
    assert isinstance(holding.library, CodeDesc)
    assert holding.library.value == "MAIN"
    assert holding.location is None
    assert isinstance(holding.call_number_type, CodeDesc)
    assert holding.call_number_type.value == "9"
    assert holding.call_number_type.desc is None

    invalid_data = MINIMAL_HOLDING_DATA.copy()
    invalid_data["location"] = ["should", "be", "dict", "or", "CodeDesc"]
    with pytest.raises(ValidationError) as exc_info:
        Holding(**invalid_data)
    assert exc_info.value.errors(include_context=False)[0]['loc'] == ('location',)
    assert 'model_type' in exc_info.value.errors(include_context=False)[0]['type']


# noinspection PyTypeChecker
def test_holding_nested_biblinkdata():
    """Test handling of nested BibLinkData model."""
    data1 = MINIMAL_HOLDING_DATA.copy()
    data1["bib_data"] = VALID_BIB_LINK_DATA_DICT
    holding1 = Holding(**data1)
    assert isinstance(holding1.bib_data, BibLinkData)
    assert holding1.bib_data.mms_id == VALID_BIB_LINK_DATA_DICT["mms_id"]

    data2 = MINIMAL_HOLDING_DATA.copy()
    data2["bib_data"] = None
    holding2 = Holding(**data2)
    assert holding2.bib_data is None

    # Invalid nested type
    data3 = MINIMAL_HOLDING_DATA.copy()
    data3["bib_data"] = "not-a-biblinkdata-dict"
    with pytest.raises(ValidationError) as exc_info:
        Holding(**data3)
    assert exc_info.value.errors(include_context=False)[0]['loc'] == ('bib_data',)
    assert 'model_type' in exc_info.value.errors(include_context=False)[0]['type']


# noinspection PyTypeChecker
def test_holding_incorrect_type_basic():
    """Test ValidationError for incorrect basic types (e.g., holding_id)."""
    invalid_data = MINIMAL_HOLDING_DATA.copy()
    invalid_data["holding_id"] = 12345
    with pytest.raises(ValidationError) as exc_info:
        Holding(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'string_type'
    assert errors[0]['loc'] == ('holding_id',)
