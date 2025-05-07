# tests/test_exceptions.py
"""Tests for custom exception classes."""

import pytest
import requests
from unittest.mock import MagicMock

# Assume xmltodict is installed for XML parsing tests
try:
    import xmltodict

    XMLTODICT_INSTALLED = True
except ImportError:
    XMLTODICT_INSTALLED = False

# Imports from the package
from api_client.exceptions import (
    AlmaApiError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    InvalidInputError
)


# --- Fixtures ---

@pytest.fixture
def mock_response(mocker) -> MagicMock:
    """Fixture to create a basic mock requests.Response object."""
    response = mocker.MagicMock(spec=requests.Response)
    response.status_code = 500  # Default to an error code
    response.url = "http://mock.url/test"
    response.headers = {}
    response.text = ""  # Default empty text body
    # Mock json() method - can be configured per test
    response.json = mocker.MagicMock()
    return response


# --- Sample Error Bodies ---

JSON_ERROR_BODY_LIST = {
    "errorList": {
        "error": [
            {
                "errorCode": "SOME_CODE",
                "errorMessage": "Detailed JSON error message.",
                "trackingId": "track123"
            }
        ]
    }
}

JSON_ERROR_BODY_SINGLE = {
    "errorList": {
        "error": {  # Single error object, not a list
            "errorCode": "SINGLE_CODE",
            "errorMessage": "Single JSON error message.",
            "trackingId": "track456"
        }
    }
}

XML_ERROR_BODY_WS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<web_service_result xmlns="">
    <errorList>
        <error>
            <errorCode>XML_CODE</errorCode>
            <errorMessage>Detailed XML error message.</errorMessage>
            <trackingId>track789</trackingId>
        </error>
    </errorList>
</web_service_result>
"""

XML_ERROR_BODY_FLAT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<errorList>
    <error>
        <errorCode>XML_FLAT_CODE</errorCode>
        <errorMessage>Flat XML error message.</errorMessage>
    </error>
</errorList>
"""

XML_ERROR_BODY_TEXT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<errorList>
    <error>Simple text error message.</error>
</errorList>
"""


# --- Tests for AlmaApiError ---

def test_alma_api_error_init_basic():
    """Test basic initialization and string representation."""
    exc = AlmaApiError("Base message")
    assert exc.status_code is None
    assert exc.response is None
    assert exc.url is None
    assert exc.detail == ""
    assert str(exc) == ": Base message"  # Includes colon from prefix logic


def test_alma_api_error_init_with_args():
    """Test initialization with status code and URL."""
    url = "http://test.com/path"
    exc = AlmaApiError("Something failed", status_code=400, url=url)
    assert exc.status_code == 400
    assert exc.response is None
    assert exc.url == url
    assert exc.detail == ""
    assert str(exc) == f"HTTP 400 for URL {url} : Something failed"


def test_alma_api_error_init_with_response_no_detail(mock_response):
    """Test initialization with response but no parsable detail."""
    mock_response.status_code = 503
    mock_response.headers = {"Content-Type": "text/plain"}
    mock_response.text = "Service Unavailable"
    # Mock json() to fail if called inappropriately
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)

    exc = AlmaApiError("Service issue", status_code=503, response=mock_response, url=mock_response.url)
    assert exc.status_code == 503
    assert exc.response == mock_response
    assert exc.url == mock_response.url
    assert exc.detail == ""  # No detail extracted
    assert str(exc) == f"HTTP 503 for URL {mock_response.url} : Service issue"


def test_alma_api_error_json_detail_list(mock_response):
    """Test detail extraction from JSON error list."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = JSON_ERROR_BODY_LIST
    # Need to set text for __init__ logic if json() isn't called first
    import json
    mock_response.text = json.dumps(JSON_ERROR_BODY_LIST)

    exc = AlmaApiError("Invalid request", status_code=400, response=mock_response, url=mock_response.url)
    assert exc.detail == "Detailed JSON error message."
    assert str(exc) == f"HTTP 400 for URL {mock_response.url} : Invalid request Detail: Detailed JSON error message."


def test_alma_api_error_json_detail_single(mock_response):
    """Test detail extraction from JSON single error object."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = JSON_ERROR_BODY_SINGLE
    import json
    mock_response.text = json.dumps(JSON_ERROR_BODY_SINGLE)

    exc = AlmaApiError("Invalid request single", status_code=400, response=mock_response, url=mock_response.url)
    assert exc.detail == "Single JSON error message."
    assert str(
        exc) == f"HTTP 400 for URL {mock_response.url} : Invalid request single Detail: Single JSON error message."


@pytest.mark.skipif(not XMLTODICT_INSTALLED, reason="xmltodict not installed")
def test_alma_api_error_xml_detail_ws(mock_response):
    """Test detail extraction from XML (web_service_result structure)."""
    mock_response.status_code = 500
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.text = XML_ERROR_BODY_WS
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)  # Ensure json fails

    exc = AlmaApiError("Server error", status_code=500, response=mock_response, url=mock_response.url)
    assert exc.detail == "Detailed XML error message."
    assert str(exc) == f"HTTP 500 for URL {mock_response.url} : Server error Detail: Detailed XML error message."


@pytest.mark.skipif(not XMLTODICT_INSTALLED, reason="xmltodict not installed")
def test_alma_api_error_xml_detail_flat(mock_response):
    """Test detail extraction from XML (flat errorList structure)."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/xml;charset=UTF-8"}  # Include charset
    mock_response.text = XML_ERROR_BODY_FLAT
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)

    exc = AlmaApiError("Bad request", status_code=400, response=mock_response, url=mock_response.url)
    assert exc.detail == "Flat XML error message."
    assert str(exc) == f"HTTP 400 for URL {mock_response.url} : Bad request Detail: Flat XML error message."


@pytest.mark.skipif(not XMLTODICT_INSTALLED, reason="xmltodict not installed")
def test_alma_api_error_xml_detail_text(mock_response):
    """Test detail extraction from XML (simple text content in error)."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.text = XML_ERROR_BODY_TEXT
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)

    exc = AlmaApiError("Simple bad request", status_code=400, response=mock_response, url=mock_response.url)
    assert exc.detail == "Simple text error message."
    assert str(exc) == f"HTTP 400 for URL {mock_response.url} : Simple bad request Detail: Simple text error message."


def test_alma_api_error_init_with_json_decode_error(mock_response):
    """Test detail extraction fails gracefully on JSONDecodeError."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)
    mock_response.text = "{invalid json"  # Provide text that would fail

    exc = AlmaApiError("Bad JSON", status_code=400, response=mock_response, url=mock_response.url)

    # --- Corrected Assertion ---
    # Check for the specific fallback message set when JSON decoding fails
    assert exc.detail == "(Failed to decode JSON response body)"
    assert "Bad JSON Detail: (Failed to decode JSON response body)" in str(exc)
    # --- End Corrected Assertion ---


@pytest.mark.skipif(not XMLTODICT_INSTALLED, reason="xmltodict not installed")
def test_alma_api_error_init_with_xml_parse_error(mock_response):
    """Test detail extraction fails gracefully on ExpatError."""
    mock_response.status_code = 500
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.text = "<unclosed>"  # Malformed XML
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("err", "doc", 0)

    exc = AlmaApiError("Bad XML", status_code=500, response=mock_response, url=mock_response.url)

    # --- Corrected Assertion ---
    # Match the actual fallback message set in the except ExpatError block
    assert exc.detail == "(Failed to parse XML response body)"
    # --- End Corrected Assertion ---
    assert "Bad XML Detail: (Failed to parse XML response body)" in str(exc)


# --- Tests for Subclasses ---

def test_subclass_inheritance():
    """Test that specific errors inherit from AlmaApiError."""
    assert isinstance(AuthenticationError(), AlmaApiError)
    assert isinstance(NotFoundError(), AlmaApiError)
    assert isinstance(RateLimitError(), AlmaApiError)
    assert isinstance(InvalidInputError(), AlmaApiError)


def test_subclass_defaults():
    """Test default messages and status codes for subclasses."""
    auth_exc = AuthenticationError()
    assert auth_exc.status_code is None  # Defaults not set in base if not provided
    assert "Authentication failed" in str(auth_exc)

    notfound_exc = NotFoundError()
    assert notfound_exc.status_code == 404
    assert "Resource not found" in str(notfound_exc)
    assert "HTTP 404" in str(notfound_exc)

    ratelimit_exc = RateLimitError()
    assert ratelimit_exc.status_code == 429
    assert "API rate limit exceeded" in str(ratelimit_exc)
    assert "HTTP 429" in str(ratelimit_exc)

    invalid_exc = InvalidInputError()
    assert invalid_exc.status_code == 400
    assert "Invalid input provided" in str(invalid_exc)
    assert "HTTP 400" in str(invalid_exc)


def test_subclass_with_args_and_detail(mock_response):
    """Test that subclasses correctly use base class __init__ for formatting and detail."""
    mock_response.status_code = 400
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = JSON_ERROR_BODY_LIST
    import json
    mock_response.text = json.dumps(JSON_ERROR_BODY_LIST)

    url = "http://test.com/invalid"
    exc = InvalidInputError(message="Specific bad input", response=mock_response, url=url)

    assert exc.status_code == 400
    assert exc.response == mock_response
    assert exc.url == url
    assert exc.detail == "Detailed JSON error message."
    expected_message = f"HTTP 400 for URL {url} : Specific bad input Detail: Detailed JSON error message."
    assert str(exc) == expected_message
