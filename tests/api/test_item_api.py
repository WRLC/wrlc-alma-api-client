# tests/api/test_item_api.py
"""Tests for the Items API in the Alma API client."""

import copy
import pytest
import requests
from unittest.mock import MagicMock
from alma_api_client.client import AlmaApiClient
from alma_api_client.api.item import ItemsAPI
from alma_api_client.models.item import Item
from alma_api_client.exceptions import AlmaApiError, NotFoundError, InvalidInputError

# --- Constants ---
TEST_MMS_ID = "991111111000541"
TEST_HOLD_ID = "222222222000541"
TEST_ITEM_PID = "233333333000541"
TEST_ITEM_BARCODE = "ITEM007"


# --- Fixtures ---

@pytest.fixture
def mock_alma_client(mocker) -> MagicMock:
    """Fixture to create a mock AlmaApiClient with mocked request methods."""
    mock_client = mocker.MagicMock(spec=AlmaApiClient)
    mock_client._get = mocker.MagicMock()
    mock_client._post = mocker.MagicMock()
    mock_client._put = mocker.MagicMock()
    mock_client._delete = mocker.MagicMock()
    return mock_client


@pytest.fixture
def item_api(mock_alma_client) -> ItemsAPI:
    """Fixture to create an ItemsAPI instance with a mocked client."""
    return ItemsAPI(mock_alma_client)


@pytest.fixture
def mock_response(mocker) -> MagicMock:
    """Fixture to create a reusable mock requests.Response object."""
    response = mocker.MagicMock(spec=requests.Response)
    response.status_code = 200
    response.headers = {'Content-Type': 'application/json'}
    response.url = f"http://mocked.url/almaws/v1/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items/mock"
    response.json = mocker.MagicMock()
    response.content = b""
    response.text = ""
    return response


@pytest.fixture
def sample_item_data_dict() -> dict:
    """Provides a valid dictionary representing ItemData."""
    return {
        "pid": TEST_ITEM_PID,
        "barcode": TEST_ITEM_BARCODE,
        "creation_date": "2023-02-10T00:00:00Z",
        "modification_date": "2024-05-01T10:00:00Z",
        "base_status": {"value": "1", "desc": "Item in place"},
        "physical_material_type": {"value": "BOOK", "desc": "Book"},
        "policy": {"value": "STANDARD", "desc": "Standard Loan"},
        "library": {"value": "MAIN", "desc": "Main Library"},
        "location": {"value": "GEN", "desc": "General Collection"},
        "description": "Test Item Desc",
        "pieces": "1",
        "public_note": "A public note",
        "requested": False  # Use actual bool
    }


@pytest.fixture
def sample_holding_link_data_dict() -> dict:
    """Provides a valid dictionary representing HoldingLinkDataForItem."""
    return {
        "holding_id": TEST_HOLD_ID,
        "link": f"http://mocked.url/almaws/v1/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}",
        "call_number": "PR6058.A69 G3 2023",
        # Use library/location keys to test alias mapping to permanent_library/location
        "library": {"value": "MAIN", "desc": "Main Library"},
        "location": {"value": "GEN", "desc": "General Collection"},
        "in_temp_location": False  # Use actual bool
    }


@pytest.fixture
def sample_bib_link_data_dict() -> dict:
    """Provides a valid dictionary representing BibLinkData."""
    return {
        "mms_id": TEST_MMS_ID,
        "title": "Parent Bib Title",
        "author": "Parent Author",
        "link": f"http://mocked.url/almaws/v1/bibs/{TEST_MMS_ID}"
    }


@pytest.fixture
def sample_item_dict(sample_item_data_dict, sample_holding_link_data_dict, sample_bib_link_data_dict) -> dict:
    """Provides a valid dictionary representing a full Item record."""
    return {
        "item_data": sample_item_data_dict,
        "holding_data": sample_holding_link_data_dict,
        "bib_data": sample_bib_link_data_dict,
        "link": f"http://mocked.url/almaws/v1/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items/{TEST_ITEM_PID}"
    }


@pytest.fixture
def sample_item_model(sample_item_dict) -> Item:
    """Provides a valid Item Pydantic model instance."""
    return Item.model_validate(sample_item_dict)


@pytest.fixture
def sample_item_list_dict(sample_item_dict) -> dict:
    """Provides a dictionary representing a list response for items."""
    item1 = sample_item_dict
    item2_data = sample_item_dict["item_data"].copy()
    item2_data["pid"] = "234444444000541"
    item2_data["barcode"] = "ITEM008"
    item2 = {
        "item_data": item2_data,
        "holding_data": sample_item_dict["holding_data"],
        "bib_data": sample_item_dict["bib_data"]
        # Link might be absent in list view
    }
    return {
        "item": [item1, item2],
        "total_record_count": 2
    }


# --- Tests for get_item ---

def test_get_item_success(item_api, mock_alma_client, mock_response, sample_item_dict):
    """Test successful retrieval and parsing of a single Item record."""
    mock_response.json.return_value = sample_item_dict
    mock_alma_client._get.return_value = mock_response

    item = item_api.get_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items/{TEST_ITEM_PID}"
    mock_alma_client._get.assert_called_once_with(
        expected_endpoint,
        headers={"Accept": "application/json"}
    )
    assert isinstance(item, Item)
    assert item.item_data.pid == TEST_ITEM_PID
    assert item.holding_data.holding_id == TEST_HOLD_ID
    assert item.bib_data.mms_id == TEST_MMS_ID
    assert item.link == sample_item_dict["link"]


def test_get_item_not_found(item_api, mock_alma_client):
    """Test get_item raises NotFoundError."""
    mock_alma_client._get.side_effect = NotFoundError(f"Item {TEST_ITEM_PID} not found.")

    with pytest.raises(NotFoundError, match=f"Item {TEST_ITEM_PID} not found."):
        item_api.get_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)


def test_get_item_validation_error(item_api, mock_alma_client, mock_response):
    """Test get_item raises AlmaApiError on Pydantic ValidationError."""
    invalid_data = {"holding_data": {}, "bib_data": {}}  # Missing required item_data
    mock_response.json.return_value = invalid_data
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match=f"Failed to validate Item response data for {TEST_ITEM_PID}"):
        item_api.get_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)


# --- Tests for get_holding_items ---

def test_get_holding_items_success_multiple(item_api, mock_alma_client, mock_response, sample_item_list_dict):
    """Test successful retrieval of multiple Items for a Holding."""
    mock_response.json.return_value = sample_item_list_dict
    mock_alma_client._get.return_value = mock_response

    items = item_api.get_holding_items(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, limit=10)

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items"
    mock_alma_client._get.assert_called_once_with(
        expected_endpoint,
        params={"limit": 10, "offset": 0},
        headers={"Accept": "application/json"}
    )
    assert isinstance(items, list)
    assert len(items) == 2
    assert isinstance(items[0], Item)
    assert isinstance(items[1], Item)
    assert items[0].item_data.pid == sample_item_list_dict["item"][0]["item_data"]["pid"]
    assert items[1].item_data.pid == sample_item_list_dict["item"][1]["item_data"]["pid"]


def test_get_holding_items_success_single(item_api, mock_alma_client, mock_response, sample_item_dict):
    """Test retrieval when API returns a single item not in a list."""
    single_item_response = {"item": sample_item_dict, "total_record_count": 1}
    mock_response.json.return_value = single_item_response
    mock_alma_client._get.return_value = mock_response

    items = item_api.get_holding_items(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID)

    assert isinstance(items, list)
    assert len(items) == 1
    assert isinstance(items[0], Item)
    assert items[0].item_data.pid == sample_item_dict["item_data"]["pid"]


def test_get_holding_items_success_zero(item_api, mock_alma_client, mock_response):
    """Test retrieval when API returns zero items."""
    mock_response.json.return_value = {"item": [], "total_record_count": 0}
    mock_alma_client._get.return_value = mock_response

    items = item_api.get_holding_items(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID)
    assert isinstance(items, list)
    assert len(items) == 0


def test_get_holding_items_parent_not_found(item_api, mock_alma_client):
    """Test get_holding_items raises NotFoundError if Bib/Holding not found."""
    mock_alma_client._get.side_effect = NotFoundError("Holding not found.")

    with pytest.raises(NotFoundError):
        item_api.get_holding_items(mms_id=TEST_MMS_ID, holding_id="notfound")


# --- Tests for create_item ---

# noinspection PyTypeChecker
def test_create_item_with_model(item_api, mock_alma_client, mock_response, sample_item_model, sample_item_dict):
    """Test creating an Item using an Item model instance."""
    mock_response.status_code = 200  # Using 200 as often seen
    # Use the full dict as the mock response, simulating Alma returning the created record
    mock_response.json.return_value = sample_item_dict
    mock_alma_client._post.return_value = mock_response

    # Prepare model for creation
    create_data_model = sample_item_model.model_copy(deep=True)
    create_data_model.item_data.pid = None  # Explicitly set to None for dump
    create_data_model.link = None

    # Calculate expected payload based *only* on model_dump used in create_item
    expected_payload = create_data_model.model_dump(
        mode='json', by_alias=True, exclude_unset=True, exclude={'link'}
    )
    # --- REMOVE manual deletion of pid ---
    # # Ensure pid is actually excluded if None, depending on pydantic settings
    # if 'item_data' in expected_payload and 'pid' in expected_payload['item_data'] and expected_payload['item_data'][
    #         'pid'] is None:
    #     del expected_payload['item_data']['pid']
    # --- End removal ---

    created_item = item_api.create_item(
        mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_record_data=create_data_model
    )

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items"
    # Assert against the payload *actually* generated by model_dump in the method
    mock_alma_client._post.assert_called_once_with(
        expected_endpoint,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload
    )
    assert isinstance(created_item, Item)
    # Assert based on the mocked response data
    assert created_item.item_data.pid == sample_item_dict["item_data"]["pid"]


def test_create_item_with_dict(item_api, mock_alma_client, mock_response, sample_item_dict):
    """Test creating an Item using a dictionary."""
    # --- Simulate a *correct* created response from Alma ---
    # Start with full data (use deepcopy just to be safe, though not strictly needed here)
    created_item_response_data = copy.deepcopy(sample_item_dict)
    # Ensure the response simulation has the PID
    created_item_response_data["item_data"]["pid"] = TEST_ITEM_PID

    mock_response.status_code = 200
    mock_response.json.return_value = created_item_response_data
    mock_alma_client._post.return_value = mock_response
    # --- End response simulation setup ---

    # Prepare the input dictionary sent *to* the API
    # --- FIX: Use deepcopy to avoid modifying response data ---
    input_dict_to_send = copy.deepcopy(sample_item_dict)
    # --- End FIX ---

    # Remove fields assigned/ignored by Alma during creation
    if 'item_data' in input_dict_to_send:
        input_dict_to_send['item_data'].pop('pid', None)
    input_dict_to_send.pop('link', None)
    if 'item_data' in input_dict_to_send:
        input_dict_to_send['item_data'].pop('creation_date', None)
        input_dict_to_send['item_data'].pop('modification_date', None)

    expected_payload = input_dict_to_send  # Payload sent is just the modified dict

    created_item = item_api.create_item(
        mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_record_data=input_dict_to_send
    )

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items"
    mock_alma_client._post.assert_called_once_with(
        expected_endpoint,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload
    )
    # Assert based on the mock *response* data
    assert isinstance(created_item, Item)
    assert created_item.item_data.pid == created_item_response_data["item_data"]["pid"]


# noinspection PyTypeChecker
def test_create_item_api_error(item_api, mock_alma_client, sample_item_model):
    """Test create_item handles API errors."""
    mock_alma_client._post.side_effect = InvalidInputError("Invalid item data provided.")
    # Prep model as if for create
    create_model = sample_item_model.model_copy(deep=True)
    create_model.item_data.pid = None
    create_model.link = None

    with pytest.raises(InvalidInputError):
        item_api.create_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_record_data=create_model)


# --- Tests for update_item ---

def test_update_item_with_model(item_api, mock_alma_client, mock_response, sample_item_model, sample_item_dict):
    """Test updating an Item using an Item model instance."""
    mock_response.json.return_value = sample_item_dict  # Return updated object
    mock_alma_client._put.return_value = mock_response

    updated_item = item_api.update_item(
        mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID, item_record_data=sample_item_model
    )

    # PUT requires the full object, don't exclude unset
    expected_payload = sample_item_model.model_dump(mode='json', by_alias=True)

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items/{TEST_ITEM_PID}"
    mock_alma_client._put.assert_called_once_with(
        expected_endpoint,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload
    )
    assert isinstance(updated_item, Item)
    assert updated_item.item_data.pid == TEST_ITEM_PID


def test_update_item_not_found(item_api, mock_alma_client, sample_item_model):
    """Test update_item raises NotFoundError."""
    mock_alma_client._put.side_effect = NotFoundError(f"Item {TEST_ITEM_PID} not found.")

    with pytest.raises(NotFoundError):
        item_api.update_item(
            mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID, item_record_data=sample_item_model
        )


# --- Tests for delete_item ---

# noinspection PyNoneFunctionAssignment
def test_delete_item_success(item_api, mock_alma_client, mock_response):
    """Test successful deletion of an Item record."""
    mock_response.status_code = 204
    mock_alma_client._delete.return_value = mock_response

    result = item_api.delete_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)

    expected_endpoint = f"/bibs/{TEST_MMS_ID}/holdings/{TEST_HOLD_ID}/items/{TEST_ITEM_PID}"
    mock_alma_client._delete.assert_called_once_with(expected_endpoint)
    assert result is None


def test_delete_item_not_found(item_api, mock_alma_client):
    """Test delete_item raises NotFoundError."""
    mock_alma_client._delete.side_effect = NotFoundError(f"Item {TEST_ITEM_PID} not found.")

    with pytest.raises(NotFoundError):
        item_api.delete_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)


def test_delete_item_api_error(item_api, mock_alma_client):
    """Test delete_item handles other API errors (e.g., item on loan)."""
    # Alma might return 400 Bad Request
    mock_alma_client._delete.side_effect = InvalidInputError("Cannot delete item involved in process.")

    with pytest.raises(InvalidInputError):
        item_api.delete_item(mms_id=TEST_MMS_ID, holding_id=TEST_HOLD_ID, item_pid=TEST_ITEM_PID)
