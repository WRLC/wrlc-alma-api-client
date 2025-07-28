"""Tests for the Item model in the Alma API Client."""

import pytest
from pydantic import ValidationError
from datetime import datetime, date, timezone
from wrlc_alma_api_client.models.bib import CodeDesc
from wrlc_alma_api_client.models.holding import BibLinkData
from wrlc_alma_api_client.models.item import Item, ItemData, HoldingLinkDataForItem


VALID_CODEDESC_BOOK = {"value": "BOOK", "desc": "Book"}
VALID_CODEDESC_MAIN_LIB = {"value": "MAIN", "desc": "Main Library"}
VALID_CODEDESC_STACKS_LOC = {"value": "STACKS", "desc": "Main Stacks"}
VALID_CODEDESC_LOAN = {"value": "LOAN", "desc": "Loan"}
VALID_CODEDESC_HOLDING_TEMP_LOC = {"value": "PROC", "desc": "Processing"}

VALID_BIB_LINK_DATA_DICT_ITEM = {
    "mms_id": "998888888000541",
    "title": "Linked Bib Title For Item",
    "link": "https://example.com/almaws/v1/bibs/998888888000541"
}

VALID_ITEM_DATA_DICT = {
    "pid": "231111111000541",
    "barcode": "ITEM001",
    "creation_date": "2023-02-10Z",
    "modification_date": "2024-05-01T10:00:00+00:00",
    "arrival_date": "2023-02-01",
    "inventory_date": "2024-01-15",
    "base_status": {"value": "0", "desc": "Item not in place"},
    "physical_material_type": VALID_CODEDESC_BOOK,
    "policy": {"value": "DEFAULT", "desc": "Default Policy"},
    "process_type": VALID_CODEDESC_LOAN,
    "library": VALID_CODEDESC_MAIN_LIB,
    "location": VALID_CODEDESC_STACKS_LOC,
    "description": "Copy 1",
    "enumeration_a": "Vol. 3",
    "chronology_i": "2023",
    "pieces": "1",
    "public_note": "Item note.",
    "is_magnetic": "false",
    "requested": "True"
}

VALID_HOLDING_LINK_DATA_DICT = {
    "holding_id": "229999999000541",
    "link": "https://example.com/almaws/v1/bibs/998888888000541/holdings/229999999000541",
    "call_number": "QA76.73.P98 P98 2023",
    "library": VALID_CODEDESC_MAIN_LIB,
    "location": VALID_CODEDESC_STACKS_LOC,
    "in_temp_location": "false",
    "temp_library": None,
    "temp_location": None
}


def test_itemdata_success_minimal():
    """Test ItemData instantiation with only required pid."""
    data = {"pid": "pid123"}
    item_data = ItemData(**data)
    assert item_data.pid == "pid123"
    assert item_data.barcode is None
    assert item_data.creation_date is None
    assert item_data.physical_material_type is None


def test_itemdata_success_full():
    """Test ItemData instantiation with full valid data."""
    item_data = ItemData(**VALID_ITEM_DATA_DICT)
    assert item_data.pid == "231111111000541"
    assert item_data.barcode == "ITEM001"
    assert item_data.creation_date == datetime(2023, 2, 10, tzinfo=timezone.utc)
    assert item_data.modification_date == datetime(2024, 5, 1, 10, tzinfo=timezone.utc)
    assert item_data.arrival_date == date(2023, 2, 1)
    assert item_data.inventory_date == date(2024, 1, 15)
    assert isinstance(item_data.base_status, CodeDesc)
    assert item_data.base_status.value == "0"
    assert isinstance(item_data.physical_material_type, CodeDesc)
    assert item_data.physical_material_type.value == "BOOK"
    assert isinstance(item_data.policy, CodeDesc)
    assert item_data.policy.value == "DEFAULT"
    assert isinstance(item_data.process_type, CodeDesc)
    assert item_data.process_type.value == "LOAN"
    assert isinstance(item_data.library, CodeDesc)
    assert item_data.library.value == "MAIN"
    assert isinstance(item_data.location, CodeDesc)
    assert item_data.location.value == "STACKS"
    assert item_data.description == "Copy 1"
    assert item_data.enumeration_a == "Vol. 3"
    assert item_data.chronology_i == "2023"
    assert item_data.pieces == "1"
    assert item_data.public_note == "Item note."
    assert item_data.is_magnetic is False
    assert item_data.requested is True


def test_itemdata_missing_required():
    """Test ValidationError when required 'pid' is missing."""
    invalid_data = VALID_ITEM_DATA_DICT.copy()
    del invalid_data["pid"]
    with pytest.raises(ValidationError) as exc_info:
        ItemData(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('pid',)


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse datetime string:")
@pytest.mark.filterwarnings("ignore:Could not parse date string:")
def test_itemdata_date_validators():
    """Test date and datetime validation for ItemData."""
    d1 = ItemData(pid="p1", creation_date="2024-01-01Z")
    assert d1.creation_date == datetime(2024, 1, 1, tzinfo=timezone.utc)

    d2 = ItemData(pid="p2", arrival_date="2024-03-15")
    assert d2.arrival_date == date(2024, 3, 15)

    d3 = ItemData(pid="p3", modification_date=None, inventory_date=None)
    assert d3.modification_date is None
    assert d3.inventory_date is None

    now_dt = datetime.now(timezone.utc)
    today_d = date.today()
    d4 = ItemData(pid="p4", creation_date=now_dt, arrival_date=today_d)
    assert d4.creation_date == now_dt
    assert d4.arrival_date == today_d

    with pytest.raises(ValidationError) as exc_dt:
        ItemData(pid="p5", modification_date="01/01/2024")
    errors_dt = exc_dt.value.errors(include_context=False)
    assert errors_dt[0]['loc'] == ('modification_date',)
    assert errors_dt[0]['type'] == 'datetime_from_date_parsing'

    with pytest.raises(ValidationError) as exc_d:
        ItemData(pid="p6", inventory_date="tomorrow")
    errors_d = exc_d.value.errors(include_context=False)
    assert errors_d[0]['loc'] == ('inventory_date',)
    assert errors_d[0]['type'] == 'date_from_datetime_parsing'


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse boolean value:")
def test_itemdata_bool_validators():
    """Test boolean validation for ItemData."""
    b1 = ItemData(pid="p1", is_magnetic="true")
    assert b1.is_magnetic is True
    b2 = ItemData(pid="p2", requested="False")
    assert b2.requested is False
    b3 = ItemData(pid="p3", is_magnetic=None, requested=False)
    assert b3.is_magnetic is None
    assert b3.requested is False

    with pytest.raises(ValidationError) as exc_inv_str:
        ItemData(pid="p4", is_magnetic="unknown")
    errors_str = exc_inv_str.value.errors(include_context=False)
    assert len(errors_str) == 1
    assert errors_str[0]['loc'] == ('is_magnetic',)
    assert errors_str[0]['type'] == 'bool_parsing'

    with pytest.raises(ValidationError) as exc_inv_type:
        ItemData(pid="p5", requested=123)
    errors_type = exc_inv_type.value.errors(include_context=False)
    assert len(errors_type) == 1
    assert errors_type[0]['loc'] == ('requested',)
    assert errors_type[0]['type'] == 'bool_parsing'


def test_holdinglink_success_minimal():
    """Test HoldingLinkDataForItem with minimal required holding_id."""
    data = {"holding_id": "h99"}
    h_link = HoldingLinkDataForItem(**data)
    assert h_link.holding_id == "h99"
    assert h_link.link is None
    assert h_link.call_number is None
    assert h_link.permanent_library is None
    assert h_link.in_temp_location is None


def test_holdinglink_success_full_and_aliases():
    """Test HoldingLinkDataForItem with full data and check aliases."""
    h_link = HoldingLinkDataForItem(**VALID_HOLDING_LINK_DATA_DICT)
    assert h_link.holding_id == "229999999000541"
    assert h_link.link == "https://example.com/almaws/v1/bibs/998888888000541/holdings/229999999000541"
    assert h_link.call_number == "QA76.73.P98 P98 2023"
    assert isinstance(h_link.permanent_library, CodeDesc)
    assert h_link.permanent_library.value == "MAIN"
    assert isinstance(h_link.permanent_location, CodeDesc)
    assert h_link.permanent_location.value == "STACKS"
    assert h_link.in_temp_location is False
    assert h_link.temp_library is None
    assert h_link.temp_location is None


def test_holdinglink_missing_required():
    """Test ValidationError when required 'holding_id' is missing."""
    invalid_data = VALID_HOLDING_LINK_DATA_DICT.copy()
    del invalid_data["holding_id"]
    with pytest.raises(ValidationError) as exc_info:
        HoldingLinkDataForItem(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('holding_id',)


# noinspection PyTypeChecker
@pytest.mark.filterwarnings("ignore:Could not parse boolean value:")
def test_holdinglink_bool_validator():
    """Test boolean validation for HoldingLinkDataForItem."""
    h1 = HoldingLinkDataForItem(holding_id="h1", in_temp_location="True")
    assert h1.in_temp_location is True
    h2 = HoldingLinkDataForItem(holding_id="h2", in_temp_location=False)
    assert h2.in_temp_location is False
    h3 = HoldingLinkDataForItem(holding_id="h3", in_temp_location=None)
    assert h3.in_temp_location is None

    with pytest.raises(ValidationError) as exc_inv_str:
        HoldingLinkDataForItem(holding_id="h4", in_temp_location="maybe")
    assert exc_inv_str.value.errors(include_context=False)[0]['loc'] == ('in_temp_location',)
    assert exc_inv_str.value.errors(include_context=False)[0]['type'] == 'bool_parsing'


def test_item_success():
    """Test successful instantiation of the main Item model with valid nested data."""
    full_item_data_dict = {
        "item_data": VALID_ITEM_DATA_DICT,
        "holding_data": VALID_HOLDING_LINK_DATA_DICT,
        "bib_data": VALID_BIB_LINK_DATA_DICT_ITEM,
        "link": "https://example.com/almaws/v1/bibs/mms/holdings/holding/items/item"
    }
    item = Item(**full_item_data_dict)
    assert isinstance(item.item_data, ItemData)
    assert item.item_data.pid == VALID_ITEM_DATA_DICT["pid"]
    assert isinstance(item.holding_data, HoldingLinkDataForItem)
    assert item.holding_data.holding_id == VALID_HOLDING_LINK_DATA_DICT["holding_id"]
    assert isinstance(item.bib_data, BibLinkData)
    assert item.bib_data.mms_id == VALID_BIB_LINK_DATA_DICT_ITEM["mms_id"]
    assert item.link is not None


# noinspection PyTypeChecker
def test_item_missing_nested_required():
    """Test ValidationError when required nested models are missing."""
    with pytest.raises(ValidationError) as exc_info_item:
        Item(holding_data=VALID_HOLDING_LINK_DATA_DICT, bib_data=VALID_BIB_LINK_DATA_DICT_ITEM)
    assert exc_info_item.value.errors(include_context=False)[0]['loc'] == ('item_data',)
    assert exc_info_item.value.errors(include_context=False)[0]['type'] == 'missing'

    with pytest.raises(ValidationError) as exc_info_holding:
        Item(item_data=VALID_ITEM_DATA_DICT, bib_data=VALID_BIB_LINK_DATA_DICT_ITEM)
    assert exc_info_holding.value.errors(include_context=False)[0]['loc'] == ('holding_data',)
    assert exc_info_holding.value.errors(include_context=False)[0]['type'] == 'missing'

    with pytest.raises(ValidationError) as exc_info_bib:
        Item(item_data=VALID_ITEM_DATA_DICT, holding_data=VALID_HOLDING_LINK_DATA_DICT)
    assert exc_info_bib.value.errors(include_context=False)[0]['loc'] == ('bib_data',)
    assert exc_info_bib.value.errors(include_context=False)[0]['type'] == 'missing'


# noinspection PyTypeChecker
def test_item_invalid_nested_type():
    """Test ValidationError when nested data has the wrong type."""
    with pytest.raises(ValidationError) as exc_info:
        Item(
            item_data="not a dict",
            holding_data=VALID_HOLDING_LINK_DATA_DICT,
            bib_data=VALID_BIB_LINK_DATA_DICT_ITEM
        )
    assert exc_info.value.errors(include_context=False)[0]['loc'] == ('item_data',)
    assert 'model_type' in exc_info.value.errors(include_context=False)[0]['type']
