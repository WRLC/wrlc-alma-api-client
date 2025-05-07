"""Tests for the Analytics API in the Alma API client."""

import pytest
import requests
from unittest.mock import MagicMock
from api_client.client import AlmaApiClient
from api_client.api.analytics import AnalyticsAPI
from api_client.models.analytics import AnalyticsReportResults, AnalyticsPath
from api_client.exceptions import AlmaApiError, NotFoundError


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
    response.json = mocker.MagicMock()
    response.content = b""
    response.text = ""
    return response


SAMPLE_PATHS_JSON = {
    "path": [
        "/shared/University/Reports/Usage Report",
        {"@path": "/shared/University/Dashboards", "@type": "Folder"}
    ]
}

SAMPLE_PATHS_XML = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AnalyticsPathsResult isFinished="true">
    <path path="/shared/University/Reports/Usage Report" type="Report"/>
    <path path="/shared/University/Dashboards" type="Folder" name="Dashboards"/>
</AnalyticsPathsResult>
"""

SAMPLE_REPORT_JSON = {
    "QueryResult": {
        "ResultXml": {
            # Simplified schema part for testing model creation
            "Schema": {
                "complexType": {
                    "@name": "Row",
                    "sequence": {
                        "element": [
                            {"@name": "Column0", "@saw-sql:columnHeading": "MMS ID", "@type": "xsd:string"},
                            {"@name": "Column1", "@saw-sql:columnHeading": "Title", "@type": "xsd:string"}
                        ]
                    }
                }
            },
            "rowset": {
                "Row": [
                    {"Column0": "99123", "Column1": "Title A"},
                    {"Column0": "99456", "Column1": "Title B"}
                ]
            }
        },
        "ResumptionToken": "token123",
        "IsFinished": "false"
    }
}

SAMPLE_REPORT_XML = b"""<?xml version="1.0" encoding="UTF-8"?> <QueryResult 
xmlns="urn:schemas-microsoft-com:xml-analysis:rowset"> <ResultXml> <rowset 
xmlns="urn:schemas-microsoft-com:xml-analysis:rowset"> <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
xmlns:saw-sql="urn:saw-sql" targetNamespace="urn:schemas-microsoft-com:xml-analysis:rowset"> <xsd:complexType 
name="Row"> <xsd:sequence> <xsd:element name="Column0" saw-sql:columnHeading="MMS ID" type="xsd:string"/> 
<xsd:element name="Column1" saw-sql:columnHeading="Title" type="xsd:string"/> </xsd:sequence> </xsd:complexType> 
</xsd:schema> <Row><Column0>99123</Column0><Column1>Title A</Column1></Row> 
<Row><Column0>99456</Column0><Column1>Title B</Column1></Row> </rowset> </ResultXml> 
<ResumptionToken>tokenXML123</ResumptionToken> <IsFinished>false</IsFinished> </QueryResult>"""


def test_list_paths_success_json(analytics_api, mock_alma_client, mock_response):
    """Test list_paths successfully parses a JSON response."""
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = SAMPLE_PATHS_JSON
    mock_alma_client._get.return_value = mock_response

    paths = analytics_api.list_paths()

    mock_alma_client._get.assert_called_once_with(
        "/analytics/paths",
        params={},
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )
    assert len(paths) == 2
    assert isinstance(paths[0], AnalyticsPath)
    assert paths[0].path == "/shared/University/Reports/Usage Report"
    assert paths[0].type is None
    assert isinstance(paths[1], AnalyticsPath)
    assert paths[1].path == "/shared/University/Dashboards"
    assert paths[1].type == "Folder"


def test_list_paths_success_xml(analytics_api, mock_alma_client, mock_response):
    """Test list_paths successfully parses an XML response."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = SAMPLE_PATHS_XML
    mock_response.text = SAMPLE_PATHS_XML.decode()
    mock_alma_client._get.return_value = mock_response

    paths = analytics_api.list_paths()

    mock_alma_client._get.assert_called_once_with(
        "/analytics/paths",
        params={},
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )
    assert len(paths) == 2
    assert isinstance(paths[0], AnalyticsPath)
    assert paths[0].path == "/shared/University/Reports/Usage Report"
    assert paths[0].type == "Report"
    assert isinstance(paths[1], AnalyticsPath)
    assert paths[1].path == "/shared/University/Dashboards"
    assert paths[1].type == "Folder"
    assert paths[1].name == "Dashboards"  # Name extracted from XML attribute


def test_list_paths_with_folder_path(analytics_api, mock_alma_client, mock_response):
    """Test list_paths calls _get with the correct folder path parameter."""
    folder = "/shared/MyFolder"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = {"path": []}  # Empty response
    mock_alma_client._get.return_value = mock_response

    analytics_api.list_paths(folder_path=folder)

    mock_alma_client._get.assert_called_once_with(
        "/analytics/paths",
        params={"path": folder},  # Check params
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )


def test_list_paths_json_decode_error(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises AlmaApiError on JSONDecodeError."""
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("mock error", "doc", 0)
    mock_alma_client._get.return_value = mock_response

    # --- Updated Match Pattern ---
    with pytest.raises(AlmaApiError, match="Failed to decode JSON response for paths:"):
        analytics_api.list_paths()


def test_list_paths_xml_parse_error(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises AlmaApiError on ExpatError."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = b"<malformed xml"
    mock_response.text = "<malformed xml"
    mock_alma_client._get.return_value = mock_response

    # --- Updated Match Pattern ---
    with pytest.raises(AlmaApiError, match="Failed to parse XML response for paths:"):
        analytics_api.list_paths()


def test_list_paths_validation_error(analytics_api, mock_alma_client, mock_response):
    """Test list_paths raises AlmaApiError on Pydantic ValidationError."""
    invalid_json_data = {"path": [{"@type": "Report"}]} # Missing required 'path'
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = invalid_json_data
    mock_alma_client._get.return_value = mock_response

    # --- Updated Match Pattern ---
    with pytest.raises(AlmaApiError, match="Failed to validate paths data:"):
        analytics_api.list_paths()


def test_list_paths_http_error(analytics_api, mock_alma_client):
    """Test list_paths propagates HTTP errors from the client."""
    mock_alma_client._get.side_effect = NotFoundError("Paths not found")

    with pytest.raises(NotFoundError, match="Paths not found"):
        analytics_api.list_paths()


# --- Tests for get_report ---

def test_get_report_success_json(analytics_api, mock_alma_client, mock_response):
    """Test get_report successfully parses a JSON response."""
    report_path = "/shared/Report1"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = SAMPLE_REPORT_JSON
    mock_alma_client._get.return_value = mock_response

    result = analytics_api.get_report(path=report_path, limit=500)

    expected_params = {"path": report_path, "limit": 500, "colNames": True}
    mock_alma_client._get.assert_called_once_with(
        "/analytics/reports",
        params=expected_params,
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )
    assert isinstance(result, AnalyticsReportResults)
    assert result.is_finished is False
    assert result.resumption_token == "token123"
    assert len(result.rows) == 2
    # Note: Column parsing from JSON isn't explicitly defined in the sample model/parser
    # assert len(result.columns) == 2
    # assert isinstance(result.columns[0], AnalyticsColumn)
    assert result.rows[0] == {"Column0": "99123", "Column1": "Title A"}
    assert result.query_path == report_path  # Check path added if not in response


def test_get_report_success_xml(analytics_api, mock_alma_client, mock_response):
    """Test get_report successfully parses an XML response (using basic parser)."""
    report_path = "/shared/Report1"
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = SAMPLE_REPORT_XML
    mock_response.text = SAMPLE_REPORT_XML.decode()
    mock_alma_client._get.return_value = mock_response

    # Expect a warning because XML parsing is less reliable/complete
    with pytest.warns(UserWarning, match="Received XML response"):
        result = analytics_api.get_report(path=report_path)

    expected_params = {"path": report_path, "limit": 1000, "colNames": True}
    mock_alma_client._get.assert_called_once_with(
        "/analytics/reports",
        params=expected_params,
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )
    assert isinstance(result, AnalyticsReportResults)
    assert result.is_finished is False
    assert result.resumption_token == "tokenXML123"
    assert len(result.rows) == 2
    # Basic XML parser just extracts ColumnN keys, doesn't map names
    assert result.rows[0] == {"Column0": "99123", "Column1": "Title A"}
    assert result.query_path == report_path


def test_get_report_with_params(analytics_api, mock_alma_client, mock_response):
    """Test get_report calls _get with all optional parameters."""
    report_path = "/shared/Report2"
    token = "abc"
    limit = 50
    filter_str = "<sawx:expr .../>"  # Example filter
    mock_response.headers = {"Content-Type": "application/json"}
    # Minimal valid response structure
    mock_response.json.return_value = {"QueryResult": {"IsFinished": "true"}}
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
        headers=pytest.approx({"Accept": "application/json, application/xml;q=0.9"})
    )


def test_get_report_json_decode_error(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises AlmaApiError on JSONDecodeError."""
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.side_effect = requests.exceptions.JSONDecodeError("mock error", "doc", 0)
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Failed to decode JSON response"):
        analytics_api.get_report(path="/some/report")


@pytest.mark.filterwarnings("ignore:Received XML response for Analytics report.*:")
def test_get_report_xml_parse_error(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises AlmaApiError on XML parsing error."""
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_response.content = b"<malformed xml"
    mock_response.text = "<malformed xml"
    mock_alma_client._get.return_value = mock_response

    with pytest.raises(AlmaApiError, match="Failed to parse Analytics XML response"):
        analytics_api.get_report(path="/some/report")


def test_get_report_validation_error(analytics_api, mock_alma_client, mock_response):
    """Test get_report raises AlmaApiError on Pydantic ValidationError."""
    # Valid JSON but missing the required 'IsFinished' flag
    invalid_report_json = {"QueryResult": {"ResumptionToken": "abc"}}
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = invalid_report_json
    mock_alma_client._get.return_value = mock_response

    # The error originates during parsing/checking before model validation here
    with pytest.raises(AlmaApiError, match="Missing 'IsFinished' flag"):
        analytics_api.get_report(path="/some/report")

    # Test case where IsFinished exists but other model validation fails
    # e.g. 'rows' is not a list
    invalid_structure_json = {"QueryResult": {"IsFinished": "true", "ResultXml": {"rowset": {"Row": "not_a_list"}}}}
    mock_response.json.return_value = invalid_structure_json
    mock_alma_client._get.return_value = mock_response  # Reset return value for this case

    with pytest.raises(AlmaApiError, match="Failed to validate API response against model"):
        analytics_api.get_report(path="/some/report")


def test_get_report_http_error(analytics_api, mock_alma_client):
    """Test get_report propagates HTTP errors from the client."""
    mock_alma_client._get.side_effect = NotFoundError("Report not found")

    with pytest.raises(NotFoundError, match="Report not found"):
        analytics_api.get_report(path="/invalid/path")
