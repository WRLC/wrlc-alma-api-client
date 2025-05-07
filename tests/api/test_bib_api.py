"""Tests for the Bib API in the Alma API client."""

import pytest
import requests
from unittest.mock import MagicMock
from wrlc.alma.api_client.client import AlmaApiClient
from wrlc.alma.api_client.api.bib import BibsAPI
from wrlc.alma.api_client.models.bib import Bib
from wrlc.alma.api_client.exceptions import AlmaApiError, NotFoundError, InvalidInputError


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
def bib_api(mock_alma_client) -> BibsAPI:
    """Fixture to create a BibsAPI instance with a mocked client."""
    return BibsAPI(mock_alma_client)


@pytest.fixture
def mock_response(mocker) -> MagicMock:
    """Fixture to create a reusable mock requests.Response object."""
    response = mocker.MagicMock(spec=requests.Response)
    response.status_code = 200
    response.headers = {'Content-Type': 'application/json'}
    response.url = "http://mocked.url/almaws/v1/bibs/mock"
    # Configure response.json() method
    response.json = mocker.MagicMock()
    # Set default empty content/text
    response.content = b""
    response.text = ""
    return response


@pytest.fixture
def sample_bib_dict() -> dict:
    """Provides a valid dictionary representing a Bib record."""
    # Based on FULL_BIB_DATA from model tests, adjusted slightly
    return {
        "mms_id": "991234567890987",
        "title": "Comprehensive Test Title",
        "author": "Author, Test A.",
        "network_number": ["(OCoLC)12345678"],
        "place_of_publication": "Testville",
        "publisher_const": "Test Publisher",
        "link": "https://example.com/almaws/v1/bibs/991234567890987",
        "suppress_from_publishing": False,  # Use bool directly
        "suppress_from_external_search": True,
        "cataloging_level": {"value": "04", "desc": "Minimal level"},
        "record_format": "marc21",
        "record": {  # Alias for record_data
            "leader": "00000cam a2200000 i 4500",
            "controlfield": [{"#text": "12345", "@tag": "001"}],
        },
        "creation_date": "2023-01-10T00:00:00Z",  # Use full ISO for consistency
        "created_by": "import_user",
        "last_modified_date": "2024-05-02T13:20:00Z",
        "last_modified_by": "system_update",
    }


@pytest.fixture
def sample_bib_model(sample_bib_dict) -> Bib:
    """Provides a valid Bib Pydantic model instance."""
    return Bib.model_validate(sample_bib_dict)


@pytest.fixture
def sample_bib_xml() -> str:
    """Provides a sample MARCXML string."""
    # Simplified MARCXML for testing purposes
    return """
    <bib>
        <record>
            <leader>00000cam a2200000 i 4500</leader>
            <controlfield tag="001">991111111000541</controlfield>
            <datafield tag="245" ind1="1" ind2="0">
                <subfield code="a">XML Test Title /</subfield>
                <subfield code="c">XML Test Author.</subfield>
            </datafield>
        </record>
    </bib>
    """


# --- Tests for get_bib ---

def test_get_bib_success(bib_api, mock_alma_client, mock_response, sample_bib_dict):
    """Test successful retrieval and parsing of a Bib record."""
    mms_id = sample_bib_dict['mms_id']
    mock_response.json.return_value = sample_bib_dict
    mock_alma_client._get.return_value = mock_response

    bib = bib_api.get_bib(mms_id=mms_id)

    mock_alma_client._get.assert_called_once_with(
        f"/bibs/{mms_id}",
        params={},
        headers={"Accept": "application/json"}
    )
    assert isinstance(bib, Bib)
    assert bib.mms_id == mms_id
    assert bib.title == sample_bib_dict['title']
    assert bib.record_data == sample_bib_dict['record']  # Check alias worked


def test_get_bib_with_params(bib_api, mock_alma_client, mock_response, sample_bib_dict):
    """Test get_bib passes view and expand parameters correctly."""
    mms_id = "123"
    view = "brief"
    expand = "p_avail,requests"
    mock_response.json.return_value = {"mms_id": mms_id, "title": "Brief"}  # Simplified response
    mock_alma_client._get.return_value = mock_response

    bib_api.get_bib(mms_id=mms_id, view=view, expand=expand)

    mock_alma_client._get.assert_called_once_with(
        f"/bibs/{mms_id}",
        params={"view": view, "expand": expand},  # Check params passed
        headers={"Accept": "application/json"}
    )


def test_get_bib_not_found(bib_api, mock_alma_client):
    """Test get_bib raises NotFoundError for 404."""
    mms_id = "notfound"
    mock_alma_client._get.side_effect = NotFoundError(f"Bib with mms_id {mms_id} not found.")

    with pytest.raises(NotFoundError, match=f"Bib with mms_id {mms_id} not found."):
        bib_api.get_bib(mms_id=mms_id)


def test_get_bib_json_error(bib_api, mock_alma_client, mock_response):
    """Test get_bib raises AlmaApiError on JSONDecodeError."""
    mms_id = "jsonerror"
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("mock decode error", "doc", 0)
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match=f"Failed to decode JSON response for MMS ID {mms_id}"):
        bib_api.get_bib(mms_id=mms_id)


def test_get_bib_validation_error(bib_api, mock_alma_client, mock_response):
    """Test get_bib raises AlmaApiError on Pydantic ValidationError."""
    mms_id = "validationerror"
    invalid_bib_data = {"title": "Only Title"}  # Missing required mms_id
    mock_response.json.return_value = invalid_bib_data
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match=f"Failed to validate Bib response data for MMS ID {mms_id}"):
        bib_api.get_bib(mms_id=mms_id)


# --- Tests for create_bib ---

def test_create_bib_with_model(bib_api, mock_alma_client, mock_response, sample_bib_model, sample_bib_dict):
    """Test creating a Bib record using a Bib model instance."""
    mock_response.status_code = 201  # Typically 200 or 201 on create/update
    mock_response.json.return_value = sample_bib_dict  # Alma returns the created record
    mock_alma_client._post.return_value = mock_response

    created_bib = bib_api.create_bib(bib_record_data=sample_bib_model)

    expected_payload = sample_bib_model.model_dump(mode='json', by_alias=True, exclude_unset=True)
    mock_alma_client._post.assert_called_once_with(
        "/bibs",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload  # Check that dumped model is sent as json
    )
    assert isinstance(created_bib, Bib)
    assert created_bib.mms_id == sample_bib_dict["mms_id"]


def test_create_bib_with_dict(bib_api, mock_alma_client, mock_response, sample_bib_dict):
    """Test creating a Bib record using a dictionary."""
    mock_response.status_code = 200
    mock_response.json.return_value = sample_bib_dict
    mock_alma_client._post.return_value = mock_response

    # Pass a valid dict (modify slightly to ensure it's not the fixture obj)
    input_dict = sample_bib_dict.copy()
    input_dict["title"] = "Dict Created Title"

    # Validate input dict against model before dumping for comparison
    expected_model = Bib.model_validate(input_dict)
    expected_payload = expected_model.model_dump(mode='json', by_alias=True, exclude_unset=True)

    created_bib = bib_api.create_bib(bib_record_data=input_dict)

    mock_alma_client._post.assert_called_once_with(
        "/bibs",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=expected_payload  # Check that validated & dumped dict is sent
    )
    assert isinstance(created_bib, Bib)
    assert created_bib.mms_id == sample_bib_dict["mms_id"]  # MMS ID likely assigned by Alma


def test_create_bib_with_xml(bib_api, mock_alma_client, mock_response, sample_bib_xml, sample_bib_dict):
    """Test creating a Bib record using an XML string."""
    mock_response.status_code = 200
    mock_response.json.return_value = sample_bib_dict  # Alma still returns JSON
    mock_alma_client._post.return_value = mock_response

    created_bib = bib_api.create_bib(bib_record_data=sample_bib_xml)

    mock_alma_client._post.assert_called_once_with(
        "/bibs",
        headers={"Accept": "application/json", "Content-Type": "application/xml"},
        data=sample_bib_xml.encode()  # Check XML sent as bytes data
    )
    assert isinstance(created_bib, Bib)
    assert created_bib.mms_id == sample_bib_dict["mms_id"]


# noinspection PyUnusedLocal
def test_create_bib_invalid_input_dict(bib_api):
    """Test create_bib raises InvalidInputError for locally invalid dict."""
    invalid_dict = {"title": "Only title"}  # Missing mms_id (though not strictly needed for create maybe?)
    # Let's test missing required field handled by Pydantic *if* needed
    # More realistically, test structure error
    invalid_dict_structure = {"mms_id": "123", "cataloging_level": "abc"}  # Invalid nested

    with pytest.raises(InvalidInputError, match="Input dictionary failed Bib model validation"):
        bib_api.create_bib(bib_record_data=invalid_dict_structure)


def test_create_bib_api_error(bib_api, mock_alma_client, sample_bib_model):
    """Test create_bib handles API errors (e.g., 400 Bad Request)."""
    mock_alma_client._post.side_effect = InvalidInputError("Invalid MARC data provided.")

    with pytest.raises(InvalidInputError, match="Invalid MARC data provided."):
        bib_api.create_bib(bib_record_data=sample_bib_model)


# --- Tests for update_bib ---

def test_update_bib_with_model(bib_api, mock_alma_client, mock_response, sample_bib_model, sample_bib_dict):
    """Test updating a Bib record using a Bib model instance."""
    mms_id = sample_bib_dict['mms_id']
    mock_response.json.return_value = sample_bib_dict  # Alma returns the updated record
    mock_alma_client._put.return_value = mock_response

    updated_bib = bib_api.update_bib(mms_id=mms_id, bib_record_data=sample_bib_model)

    # PUT requires the full object, don't exclude unset by default
    expected_payload = sample_bib_model.model_dump(mode='json', by_alias=True)
    mock_alma_client._put.assert_called_once_with(
        f"/bibs/{mms_id}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params={},  # No extra params in this call
        json=expected_payload
    )
    assert isinstance(updated_bib, Bib)
    assert updated_bib.mms_id == mms_id


def test_update_bib_with_params(bib_api, mock_alma_client, mock_response, sample_bib_model, sample_bib_dict):
    """Test update_bib passes optional query parameters."""
    mms_id = sample_bib_dict['mms_id']
    mock_response.json.return_value = sample_bib_dict
    mock_alma_client._put.return_value = mock_response

    bib_api.update_bib(mms_id=mms_id, bib_record_data=sample_bib_model, override_warning=True)

    expected_payload = sample_bib_model.model_dump(mode='json', by_alias=True)
    mock_alma_client._put.assert_called_once_with(
        f"/bibs/{mms_id}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params={"override_warning": "true"},  # Check params passed
        json=expected_payload
    )


def test_update_bib_not_found(bib_api, mock_alma_client, sample_bib_model):
    """Test update_bib raises NotFoundError."""
    mms_id = "notfound"
    mock_alma_client._put.side_effect = NotFoundError(f"Bib {mms_id} not found.")

    with pytest.raises(NotFoundError):
        bib_api.update_bib(mms_id=mms_id, bib_record_data=sample_bib_model)


# --- Tests for delete_bib ---

# noinspection PyNoneFunctionAssignment
def test_delete_bib_success(bib_api, mock_alma_client, mock_response):
    """Test successful deletion of a Bib record."""
    mms_id = "todelete"
    # Mock _delete to return something (doesn't matter what, as long as no exception)
    # The client's _handle_response_errors should handle 204 status internally
    mock_response.status_code = 204
    mock_alma_client._delete.return_value = mock_response

    result = bib_api.delete_bib(mms_id=mms_id)

    mock_alma_client._delete.assert_called_once_with(
        f"/bibs/{mms_id}",
        params={}
    )
    assert result is None  # Expect None on successful deletion


def test_delete_bib_with_params(bib_api, mock_alma_client, mock_response):
    """Test delete_bib passes optional query parameters."""
    mms_id = "todelete"
    reason = "Withdraw"
    mock_response.status_code = 204
    mock_alma_client._delete.return_value = mock_response

    bib_api.delete_bib(mms_id=mms_id, override_warning=False, reason=reason)

    mock_alma_client._delete.assert_called_once_with(
        f"/bibs/{mms_id}",
        params={"override_warning": "false", "reason": reason}  # Check params
    )


def test_delete_bib_not_found(bib_api, mock_alma_client):
    """Test delete_bib raises NotFoundError."""
    mms_id = "notfound"
    mock_alma_client._delete.side_effect = NotFoundError(f"Bib {mms_id} not found.")

    with pytest.raises(NotFoundError):
        bib_api.delete_bib(mms_id=mms_id)


def test_delete_bib_api_error(bib_api, mock_alma_client):
    """Test delete_bib handles generic API errors."""
    mms_id = "error"
    # Example: Alma might return 400 if bib has related inventory
    mock_alma_client._delete.side_effect = InvalidInputError("Cannot delete record with inventory.")

    with pytest.raises(InvalidInputError, match="Cannot delete record with inventory."):
        bib_api.delete_bib(mms_id=mms_id)
