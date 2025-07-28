"""Tests for the Analytics API in the Alma API client."""

import pytest
import requests
from unittest.mock import MagicMock
from wrlc_alma_api_client.client import AlmaApiClient
from wrlc_alma_api_client.api.analytics import AnalyticsAPI
from wrlc_alma_api_client.models.analytics import AnalyticsReportResults, AnalyticsPath
from wrlc_alma_api_client.exceptions import AlmaApiError, NotFoundError


@pytest.fixture
def mock_alma_client(mocker) -> MagicMock:
    """Fixture to create a mock AlmaApiClient."""
    mock_client = mocker.MagicMock(spec=AlmaApiClient)
    mock_client._get = mocker.MagicMock()
    return mock_client


@pytest.fixture
def analytics_api(mock_alma_client) -> AnalyticsAPI:
    """Fixture to create an AnalyticsAPI instance with a mocked client."""
    return AnalyticsAPI(mock_alma_client)


@pytest.fixture
def mock_response(mocker) -> MagicMock:
    """Fixture to create a mock requests.Response object."""
    response = mocker.MagicMock(spec=requests.Response)
    response.status_code = 200
    response.headers = {}
    response.url = "http://mocked.url/almaws/v1/analytics/mock"
    # No need for response.json as we are XML focused now
    response.content = b""
    response.text = ""
    return response


SAMPLE_PATHS_XML = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AnalyticsPathsResult isFinished="true">
    <path path="/shared/University/Reports/Usage Report" type="Report"/>
    <path path="/shared/University/Dashboards" type="Folder" name="Dashboards"/>
</AnalyticsPathsResult>
"""

# SAMPLE_REPORT_JSON is no longer needed
# SAMPLE_REPORT_JSON = { ... }

SAMPLE_REPORT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<report>
    <QueryResult xmlns="urn:schemas-microsoft-com:xml-analysis:rowset">
        <ResultXml>
            <rowset xmlns="urn:schemas-microsoft-com:xml-analysis:rowset">
                <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:saw-sql="urn:saw-sql" 
                targetNamespace="urn:schemas-microsoft-com:xml-analysis:rowset">
                    <xsd:complexType name="Row">
                        <xsd:sequence>
                            <xsd:element name="Column0" saw-sql:columnHeading="MMS ID" type="xsd:string"/>
                            <xsd:element name="Column1" saw-sql:columnHeading="Title" type="xsd:string"/>
                        </xsd:sequence>
                    </xsd:complexType>
                </xsd:schema>
                <Row><Column0>99123</Column0><Column1>Title A</Column1></Row>
                <Row><Column0>99456</Column0><Column1>Title B</Column1></Row>
            </rowset>
        </ResultXml>
        <ResumptionToken>tokenXML123</ResumptionToken>
        <IsFinished>false</IsFinished>
    </QueryResult>
</report>"""


# Test for list_paths (XML only)
def test_list_paths_success_xml(analytics_api, mock_alma_client, mock_response):
    """Test list_paths successfully parses an XML response."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = SAMPLE_PATHS_XML
    mock_alma_client._get.return_value = mock_response

    paths = analytics_api.list_paths()

    mock_alma_client._get.assert_called_once_with(
        "/analytics/paths",
        params={},
        headers={"Accept": "application/xml"}  # Updated expected header
    )
    assert len(paths) == 2
    assert isinstance(paths[0], AnalyticsPath)
    assert paths[0].path == "/shared/University/Reports/Usage Report"
    assert paths[0].type == "Report"
    assert isinstance(paths[1], AnalyticsPath)
    assert paths[1].path == "/shared/University/Dashboards"
    assert paths[1].type == "Folder"
    assert paths[1].name == "Dashboards"


def test_list_paths_with_folder_path(analytics_api, mock_alma_client, mock_response):
    """Test list_paths calls _get with the correct folder path parameter, expecting XML."""
    folder = "/shared/MyFolder"
    mock_response.headers = {"Content-Type": "application/xml"}  # Expect XML
    mock_response.content = (b"<AnalyticsPathsResult isFinished='true'>"
                             b"<path path='/shared/MyFolder/ReportA' type='Report'/></AnalyticsPathsResult>")
    mock_alma_client._get.return_value = mock_response

    analytics_api.list_paths(folder_path=folder)

    mock_alma_client._get.assert_called_once_with(
        "/analytics/paths",
        params={"path": folder},
        headers={"Accept": "application/xml"}  # Updated expected header
    )


def test_list_paths_xml_parse_error(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises AlmaApiError on ExpatError."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = b"<malformed xml"
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Failed to parse XML response for paths:"):
        analytics_api.list_paths()


def test_list_paths_validation_error_xml(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises AlmaApiError on Pydantic ValidationError with XML input."""
    # XML that is valid but whose content will fail Pydantic validation for AnalyticsPath
    # e.g. a <path> element missing the required 'path' attribute
    invalid_xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <AnalyticsPathsResult isFinished="true">
        <path type="Report"/> 
    </AnalyticsPathsResult>
    """
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = invalid_xml_data
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Failed to validate paths data:"):
        analytics_api.list_paths()


def test_list_paths_unexpected_content_type(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises error if non-XML content type is received."""
    mock_response.headers = {"Content-Type": "application/json"}  # Simulate unexpected JSON
    mock_response.json.return_value = {}  # Mock json() if it were called
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Unexpected Content-Type for paths: application/json. Expected XML."):
        analytics_api.list_paths()


def test_list_paths_http_error(analytics_api, mock_alma_client):
    """Test list_paths propagates HTTP errors from the client."""
    mock_alma_client._get.side_effect = NotFoundError("Paths not found")

    with pytest.raises(NotFoundError, match="Paths not found"):
        analytics_api.list_paths()


# --- Tests for get_report (XML only) ---

def test_get_report_success_xml(analytics_api, mock_alma_client, mock_response):
    """Test get_report successfully parses an XML response and remaps columns."""
    report_path = "/shared/Report1"
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = SAMPLE_REPORT_XML
    mock_alma_client._get.return_value = mock_response

    # Removed pytest.warns as the warning is no longer issued
    result = analytics_api.get_report(path=report_path)

    expected_params = {"path": report_path, "limit": 1000, "colNames": True}
    mock_alma_client._get.assert_called_once_with(
        "/analytics/reports",
        params=expected_params,
        headers={"Accept": "application/xml"}  # Updated expected header
    )
    assert isinstance(result, AnalyticsReportResults)
    assert result.is_finished is False
    assert result.resumption_token == "tokenXML123"
    assert len(result.rows) == 2
    # Assert remapped column names
    assert result.rows[0] == {"MMS ID": "99123", "Title": "Title A"}
    assert result.rows[1] == {"MMS ID": "99456", "Title": "Title B"}
    assert len(result.columns) == 2
    assert result.columns[0].name == "MMS ID"
    assert result.columns[1].name == "Title"
    assert result.query_path == report_path


def test_get_report_with_params(analytics_api, mock_alma_client, mock_response):
    """Test get_report calls _get with all optional parameters, expecting XML."""
    report_path = "/shared/Report2"
    token = "abc"
    limit = 50
    filter_str = "<sawx:expr .../>"
    mock_response.headers = {"Content-Type": "application/xml"}  # Expect XML
    # Minimal valid XML response
    mock_response.content = b"<report><QueryResult><IsFinished>true</IsFinished></QueryResult></report>"
    mock_alma_client._get.return_value = mock_response

    analytics_api.get_report(
        path=report_path,
        limit=limit,
        column_names=False,
        resumption_token=token,
        filter_xml=filter_str
    )

    expected_params = {
        "path": report_path,
        "limit": limit,
        "colNames": False,
        "token": token,
        "filter": filter_str
    }
    mock_alma_client._get.assert_called_once_with(
        "/analytics/reports",
        params=expected_params,
        headers={"Accept": "application/xml"}  # Updated expected header
    )


def test_get_report_xml_parse_error(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises AlmaApiError on XML parsing error."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = b"<malformed xml"
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Failed to parse Analytics XML response"):
        analytics_api.get_report(path="/some/report")


def test_get_report_validation_error_xml(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises AlmaApiError on Pydantic ValidationError with XML input."""
    # Test case 1: Missing 'IsFinished' flag in the parsed XML structure
    xml_missing_isfinished = b"""<?xml version="1.0" encoding="UTF-8"?>
    <report>
        <QueryResult>
            <ResumptionToken>abc</ResumptionToken>
            <!-- IsFinished is missing -->
        </QueryResult>
    </report>
    """
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = xml_missing_isfinished
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Missing 'IsFinished' flag in <QueryResult> after parsing XML response."):
        analytics_api.get_report(path="/some/report")

    # Test case 2: XML leads to data that fails Pydantic model validation
    # e.g. IsFinished has an invalid boolean string
    xml_invalid_isfinished_value = b"""<?xml version="1.0" encoding="UTF-8"?>
    <report>
        <QueryResult>
            <IsFinished>maybe</IsFinished> 
        </QueryResult>
    </report>
    """
    mock_response.content = xml_invalid_isfinished_value  # Update content for the same mock_response
    mock_alma_client._get.return_value = mock_response  # Re-assign if necessary, though it's the same object

    with pytest.raises(AlmaApiError, match="Failed to validate API response against model"):
        analytics_api.get_report(path="/some/report")


def test_get_report_unexpected_content_type(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises error if non-XML content type is received."""
    mock_response.headers = {"Content-Type": "application/json"}  # Simulate unexpected JSON
    # mock_response.json.return_value = {} # Not strictly needed as it should fail before json parsing
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Unexpected Content-Type received: application/json. Expected XML."):
        analytics_api.get_report(path="/some/report")


def test_get_report_http_error(analytics_api, mock_alma_client):
    """Test get_report propagates HTTP errors from the client."""
    mock_alma_client._get.side_effect = NotFoundError("Report not found")

    with pytest.raises(NotFoundError, match="Report not found"):
        analytics_api.get_report(path="/invalid/path")
