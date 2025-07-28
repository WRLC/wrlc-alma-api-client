# tests/api/test_holding_api.py
"""Tests for the Holdings API in the Alma API client."""

import pytest
import requests
from unittest.mock import MagicMock

# Imports from the package
from wrlc_alma_api_client.client import AlmaApiClient
from wrlc_alma_api_client.api.holding import HoldingsAPI
from wrlc_alma_api_client.models.holding import Holding  # Import Holding and BibLinkData
from wrlc_alma_api_client.exceptions import AlmaApiError, NotFoundError, InvalidInputError


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
def holding_api(mock_alma_client) -> HoldingsAPI:
    """Fixture to create a HoldingsAPI instance with a mocked client."""
    return HoldingsAPI(mock_alma_client)


@pytest.fixture
def mock_response(mocker) -> MagicMock:
    """Fixture to create a reusable mock requests.Response object."""
    response = mocker.MagicMock(spec=requests.Response)
    response.status_code = 200
    response.headers = {'Content-Type': 'application/json'}
    response.url = "http://mocked.url/almaws/v1/bibs/mms1/holdings/mock"
    response.json = mocker.MagicMock()
    response.content = b""
    response.text = ""
    return response


@pytest.fixture
def sample_holding_dict() -> dict:
    """Provides a valid dictionary representing a Holding record."""
    # Based on FULL_HOLDING_DATA from model tests, adjusted slightly
    return {
        "holding_id": "229999999000541",
        "link": "https://example.com/almaws/v1/bibs/998888888000541/holdings/229999999000541",
        "created_by": "migration_user",
        "created_date": "2022-11-01T00:00:00Z",  # Full ISO
        "last_modified_by": "circ_desk",
        "last_modified_date": "2024-04-15T09:00:00Z",  # Full ISO
        "suppress_from_publishing": False,
        "library": {"value": "MAIN", "desc": "Main Library"},
        "location": {"value": "STACKS", "desc": "Main Stacks"},
        "call_number_type": {"value": "0", "desc": "Library of Congress classification"},
        "call_number": "QA76.73.P98 P98 2023",
        "copy_id": "c.1",
        "anies": {  # Alias for record_data
            "leader": "00000nu  a2200000un 4500",
            "controlfield": [{"#text": "229999999000541", "@tag": "001"}]
        },
        "bib_data": {
            "mms_id": "998888888000541",
            "title": "Linked Bib Title",
            "link": "https://example.com/almaws/v1/bibs/998888888000541"
        }
    }


@pytest.fixture
def sample_holding_model(sample_holding_dict) -> Holding:
    """Provides a valid Holding Pydantic model instance."""
    return Holding.model_validate(sample_holding_dict)


@pytest.fixture
def sample_holding_list_dict(sample_holding_dict) -> dict:
    """Provides a dictionary representing a list response for holdings."""
    holding1 = sample_holding_dict
    holding2 = sample_holding_dict.copy()
    holding2["holding_id"] = "228888888000541"
    holding2["copy_id"] = "c.2"
    holding2["anies"] = {"leader": "..."}  # simplified
    return {
        "holding": [holding1, holding2],
        "total_record_count": 2
    }


@pytest.fixture
def sample_holding_xml() -> str:
    """Provides a sample Holding MARCXML string."""
    # Simplified XML for testing purposes
    return """
    <holding>
        <holding_id>225555555000541</holding_id>
        <location library="MAIN">STACKS</location>
        <call_number>TEMP CALL</call_number>
        </holding>
    """


# --- Tests for get_holding ---

def test_get_holding_success(holding_api, mock_alma_client, mock_response, sample_holding_dict):
    """Test successful retrieval and parsing of a single Holding record."""
    mms_id = sample_holding_dict["bib_data"]["mms_id"]
    holding_id = sample_holding_dict["holding_id"]
    mock_response.json.return_value = sample_holding_dict
    mock_alma_client._get.return_value = mock_response

    holding = holding_api.get_holding(mms_id=mms_id, holding_id=holding_id)

    mock_alma_client._get.assert_called_once_with(
        f"/bibs/{mms_id}/holdings/{holding_id}",
        headers={"Accept": "application/json"}
    )
    assert isinstance(holding, Holding)
    assert holding.holding_id == holding_id
    assert holding.library.value == "MAIN"
    assert holding.record_data["leader"] == sample_holding_dict["anies"]["leader"]  # Check alias


def test_get_holding_not_found(holding_api, mock_alma_client):
    """Test get_holding raises NotFoundError."""
    mms_id = "bib1"
    holding_id = "notfound"
    mock_alma_client._get.side_effect = NotFoundError(f"Holding {holding_id} not found.")

    with pytest.raises(NotFoundError, match=f"Holding {holding_id} not found."):
        holding_api.get_holding(mms_id=mms_id, holding_id=holding_id)


def test_get_holding_validation_error(holding_api, mock_alma_client, mock_response):
    """Test get_holding raises AlmaApiError on Pydantic ValidationError."""
    mms_id = "bib1"
    holding_id = "validationerror"
    invalid_data = {"library": {"value": "MAIN"}}  # Missing required holding_id
    mock_response.json.return_value = invalid_data
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match=f"Failed to validate Holding response data for {holding_id}"):
        holding_api.get_holding(mms_id=mms_id, holding_id=holding_id)


# --- Tests for get_bib_holdings ---

def test_get_bib_holdings_success_multiple(holding_api, mock_alma_client, mock_response, sample_holding_list_dict):
    """Test successful retrieval of multiple Holdings for a Bib."""
    mms_id = "bib_with_many_holdings"
    mock_response.json.return_value = sample_holding_list_dict
    mock_alma_client._get.return_value = mock_response

    holdings = holding_api.get_bib_holdings(mms_id=mms_id, limit=10)

    mock_alma_client._get.assert_called_once_with(
        f"/bibs/{mms_id}/holdings",
        params={"limit": 10, "offset": 0},
        headers={"Accept": "application/json"}
    )
    assert isinstance(holdings, list)
    assert len(holdings) == 2
    assert isinstance(holdings[0], Holding)
    assert isinstance(holdings[1], Holding)
    assert holdings[0].holding_id == sample_holding_list_dict["holding"][0]["holding_id"]
    assert holdings[1].holding_id == sample_holding_list_dict["holding"][1]["holding_id"]


def test_get_bib_holdings_success_single(holding_api, mock_alma_client, mock_response, sample_holding_dict):
    """Test retrieval when API returns a single holding not in a list."""
    mms_id = "bib_with_one_holding"
    # Simulate API returning single object under 'holding' key
    single_item_response = {"holding": sample_holding_dict, "total_record_count": 1}
    mock_response.json.return_value = single_item_response
    mock_alma_client._get.return_value = mock_response

    holdings = holding_api.get_bib_holdings(mms_id=mms_id)

    assert isinstance(holdings, list)
    assert len(holdings) == 1
    assert isinstance(holdings[0], Holding)
    assert holdings[0].holding_id == sample_holding_dict["holding_id"]


def test_get_bib_holdings_success_zero(holding_api, mock_alma_client, mock_response):
    """Test retrieval when API returns zero holdings."""
    mms_id = "bib_with_no_holdings"
    zero_item_response = {"holding": [], "total_record_count": 0}  # Empty list
    zero_item_response_alt = {"total_record_count": 0}  # Or maybe key is missing entirely
    mock_response.json.return_value = zero_item_response
    mock_alma_client._get.return_value = mock_response

    holdings = holding_api.get_bib_holdings(mms_id=mms_id)
    assert isinstance(holdings, list)
    assert len(holdings) == 0

    # Test alternative zero response
    mock_response.json.return_value = zero_item_response_alt
    mock_alma_client._get.return_value = mock_response
    holdings_alt = holding_api.get_bib_holdings(mms_id=mms_id)
    assert isinstance(holdings_alt, list)
    assert len(holdings_alt) == 0


def test_get_bib_holdings_bib_not_found(holding_api, mock_alma_client):
    """Test get_bib_holdings raises NotFoundError if Bib not found."""
    mms_id = "notfound"
    mock_alma_client._get.side_effect = NotFoundError(f"Bib {mms_id} not found.")

    with pytest.raises(NotFoundError):
        holding_api.get_bib_holdings(mms_id=mms_id)


# --- Tests for create_holding ---

def test_create_holding_with_model(holding_api, mock_alma_client, mock_response, sample_holding_model,
                                   sample_holding_dict):
    """Test creating a Holding using a Holding model instance."""
    mms_id = sample_holding_dict["bib_data"]["mms_id"]
    mock_response.status_code = 200  # Often 200 for create/update
    mock_response.json.return_value = sample_holding_dict  # Return created object
    mock_alma_client._post.return_value = mock_response

    # Create model might not have holding_id or link yet
    create_model = sample_holding_model.model_copy(update={"holding_id": None, "link": None})
    expected_payload = create_model.model_dump(mode='json', by_alias=True, exclude_unset=True)

    created_holding = holding_api.create_holding(mms_id=mms_id, holding_record_data=create_model)

    mock_alma_client._post.assert_called_once_with(
        f"/bibs/{mms_id}/holdings",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload
    )
    assert isinstance(created_holding, Holding)
    assert created_holding.holding_id == sample_holding_dict["holding_id"]  # ID assigned by Alma


def test_create_holding_with_dict(holding_api, mock_alma_client, mock_response, sample_holding_dict):
    """Test creating a Holding using a dictionary."""
    mms_id = sample_holding_dict["bib_data"]["mms_id"]
    mock_response.json.return_value = sample_holding_dict  # Simulate Alma returning full record
    mock_alma_client._post.return_value = mock_response

    input_dict = sample_holding_dict.copy()
    # Remove fields assigned by Alma post-creation or system fields usually not sent
    input_dict.pop("holding_id", None)
    input_dict.pop("link", None)
    input_dict.pop("created_date", None)
    input_dict.pop("last_modified_date", None)
    input_dict.pop("created_by", None)
    input_dict.pop("last_modified_by", None)
    # Keep bib_data as it might be needed contextually by API, but remove its link/system fields if present
    if 'bib_data' in input_dict and isinstance(input_dict['bib_data'], dict):
        input_dict['bib_data'].pop('link', None)

    # --- FIX: Remove local validation and adjust payload assertion ---
    # expected_model = Holding.model_validate(input_dict) # REMOVE THIS
    # expected_payload = expected_model.model_dump(...) # REMOVE THIS
    expected_payload = input_dict  # Payload sent is just the modified dict
    # ---------------------------------------------------------------

    created_holding = holding_api.create_holding(mms_id=mms_id, holding_record_data=input_dict)

    mock_alma_client._post.assert_called_once_with(
        f"/bibs/{mms_id}/holdings",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload  # Assert the raw dict was sent
    )
    assert isinstance(created_holding, Holding)
    # Assert based on the response mock, which includes holding_id
    assert created_holding.holding_id == sample_holding_dict["holding_id"]


def test_create_holding_api_error(holding_api, mock_alma_client, sample_holding_model):
    """Test create_holding handles API errors."""
    mms_id = "bib1"
    mock_alma_client._post.side_effect = InvalidInputError("Invalid holding data provided.")
    # Create model might not have holding_id or link yet
    create_model = sample_holding_model.model_copy(update={"holding_id": None, "link": None})

    with pytest.raises(InvalidInputError):
        holding_api.create_holding(mms_id=mms_id, holding_record_data=create_model)


# --- Tests for update_holding ---

def test_update_holding_with_model(holding_api, mock_alma_client, mock_response, sample_holding_model,
                                   sample_holding_dict):
    """Test updating a Holding using a Holding model instance."""
    mms_id = sample_holding_dict["bib_data"]["mms_id"]
    holding_id = sample_holding_dict["holding_id"]
    mock_response.json.return_value = sample_holding_dict  # Return updated object
    mock_alma_client._put.return_value = mock_response

    updated_holding = holding_api.update_holding(mms_id=mms_id, holding_id=holding_id,
                                                 holding_record_data=sample_holding_model)

    # PUT requires the full object, don't exclude unset
    expected_payload = sample_holding_model.model_dump(mode='json', by_alias=True)

    mock_alma_client._put.assert_called_once_with(
        f"/bibs/{mms_id}/holdings/{holding_id}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload
    )
    assert isinstance(updated_holding, Holding)
    assert updated_holding.holding_id == holding_id


def test_update_holding_not_found(holding_api, mock_alma_client, sample_holding_model):
    """Test update_holding raises NotFoundError."""
    mms_id = "bib1"
    holding_id = "notfound"
    mock_alma_client._put.side_effect = NotFoundError(f"Holding {holding_id} not found.")

    with pytest.raises(NotFoundError):
        holding_api.update_holding(mms_id=mms_id, holding_id=holding_id, holding_record_data=sample_holding_model)


# --- Tests for delete_holding ---

# noinspection PyNoneFunctionAssignment
def test_delete_holding_success(holding_api, mock_alma_client, mock_response):
    """Test successful deletion of a Holding record."""
    mms_id = "bib1"
    holding_id = "todelete"
    mock_response.status_code = 204  # No Content
    mock_alma_client._delete.return_value = mock_response

    result = holding_api.delete_holding(mms_id=mms_id, holding_id=holding_id)

    mock_alma_client._delete.assert_called_once_with(
        f"/bibs/{mms_id}/holdings/{holding_id}"
    )
    assert result is None  # Expect None on success


def test_delete_holding_not_found(holding_api, mock_alma_client):
    """Test delete_holding raises NotFoundError."""
    mms_id = "bib1"
    holding_id = "notfound"
    mock_alma_client._delete.side_effect = NotFoundError(f"Holding {holding_id} not found.")

    with pytest.raises(NotFoundError):
        holding_api.delete_holding(mms_id=mms_id, holding_id=holding_id)


def test_delete_holding_error(holding_api, mock_alma_client):
    """Test delete_holding handles other API errors (e.g., holding has items)."""
    mms_id = "bib1"
    holding_id = "hasitems"
    # Alma often returns 400 Bad Request in this case
    mock_alma_client._delete.side_effect = InvalidInputError("Cannot delete holding with items.")

    with pytest.raises(InvalidInputError, match="Cannot delete holding with items"):
        holding_api.delete_holding(mms_id=mms_id, holding_id=holding_id)
