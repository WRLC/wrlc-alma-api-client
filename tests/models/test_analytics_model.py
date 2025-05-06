"""Tests for the Analytics models in the Alma API client."""

import warnings
import pytest
from pydantic import ValidationError

from wrlc_alma_api_client.models.analytics import (
    AnalyticsColumn,
    AnalyticsReportResults,
    AnalyticsPath
)


def test_analytics_column_success():
    """Test successful instantiation of AnalyticsColumn with required data."""
    col_data = {"name": "Title", "data_type": "string"}
    col = AnalyticsColumn(**col_data)
    assert col.name == "Title"
    assert col.data_type == "string"


def test_analytics_column_optional_fields():
    """Test successful instantiation with only required fields."""
    col_data = {"name": "MMS ID"}
    col = AnalyticsColumn(**col_data)
    assert col.name == "MMS ID"
    assert col.data_type is None


def test_analytics_column_missing_required_field():
    """Test ValidationError when required 'name' field is missing."""
    col_data = {"data_type": "integer"}
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsColumn(**col_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('name',)


def test_analytics_column_incorrect_type():
    """Test ValidationError when 'name' field has incorrect type."""
    col_data = {"name": 123}
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsColumn(**col_data)
    assert "Input should be a valid string" in str(exc_info.value)


VALID_COLUMN_DATA = [{"name": "MMS ID", "data_type": "string"}, {"name": "Title"}]
VALID_ROW_DATA = [{"MMS ID": "12345", "Title": "Test Title 1"}, {"MMS ID": "67890", "Title": "Test Title 2"}]

MINIMAL_VALID_REPORT_DATA = {"IsFinished": True}

FULL_VALID_REPORT_DATA = {
    "columns": VALID_COLUMN_DATA,
    "rows": VALID_ROW_DATA,
    "IsFinished": False,
    "ResumptionToken": "token123",
    "query_path": "/shared/Reports/MyReport",
    "job_id": "job-abc"
}


def test_analytics_report_results_success_minimal():
    """Test successful instantiation with minimal required data (using alias)."""
    report = AnalyticsReportResults(**MINIMAL_VALID_REPORT_DATA)
    assert report.is_finished is True
    assert report.resumption_token is None
    assert report.columns == []
    assert report.rows == []  # Default factory
    assert report.query_path is None
    assert report.job_id is None


def test_analytics_report_results_success_full():
    """Test successful instantiation with all fields populated (using aliases)."""
    report = AnalyticsReportResults(**FULL_VALID_REPORT_DATA)

    assert report.is_finished is False
    assert report.resumption_token == "token123"
    assert report.query_path == "/shared/Reports/MyReport"
    assert report.job_id == "job-abc"

    assert len(report.columns) == 2
    assert isinstance(report.columns[0], AnalyticsColumn)
    assert report.columns[0].name == "MMS ID"
    assert report.columns[1].name == "Title"

    assert len(report.rows) == 2
    assert report.rows[0] == {"MMS ID": "12345", "Title": "Test Title 1"}
    assert report.rows[1] == {"MMS ID": "67890", "Title": "Test Title 2"}


def test_analytics_report_results_missing_required():
    """Test ValidationError when required 'is_finished' (alias 'IsFinished') is missing."""
    invalid_data = {
        "columns": VALID_COLUMN_DATA,
        "rows": VALID_ROW_DATA,
        "ResumptionToken": "token123"
    }
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsReportResults(**invalid_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('IsFinished',)


def test_analytics_report_results_incorrect_type_bool():
    """Test ValidationError when 'is_finished' has incorrect type."""
    invalid_data = {"IsFinished": "maybe_not"}
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsReportResults(**invalid_data)
    assert "Input should be a valid boolean" in str(exc_info.value)


def test_analytics_report_results_incorrect_type_list():
    """Test ValidationError when 'columns' or 'rows' are not lists."""
    invalid_data_cols = {"IsFinished": True, "columns": "not_a_list"}
    with pytest.raises(ValidationError):
        AnalyticsReportResults(**invalid_data_cols)

    invalid_data_rows = {"IsFinished": True, "rows": "not_a_list"}
    with pytest.raises(ValidationError):
        AnalyticsReportResults(**invalid_data_rows)


def test_analytics_report_results_optional_fields_absent():
    """Test optional fields are None when absent from input."""
    report = AnalyticsReportResults(**MINIMAL_VALID_REPORT_DATA)
    assert report.resumption_token is None
    assert report.query_path is None
    assert report.job_id is None


def test_analytics_report_results_token_present_when_not_finished():
    """Test instantiation works correctly when not finished and token is present."""
    data = {"IsFinished": False, "ResumptionToken": "abc"}
    report = AnalyticsReportResults(**data)
    assert report.is_finished is False
    assert report.resumption_token == "abc"


def test_analytics_report_results_warns_when_incomplete_no_token():
    """Test that a warning is raised if results are not finished but no token is provided."""
    data = {"IsFinished": False, "ResumptionToken": None}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        report = AnalyticsReportResults(**data)
        assert report.is_finished is False
        assert report.resumption_token is None

        assert len(w) >= 1
        assert issubclass(w[-1].category, UserWarning)
        assert ("results for path 'unknown' are incomplete (is_finished=False) but no resumption_token was "
                "provided") in str(w[-1].message)


def test_analytics_path_success_minimal():
    """Test successful instantiation with minimal required data."""
    path_data = {"path": "/shared/Reports/Usage"}
    path = AnalyticsPath(**path_data)
    assert path.path == "/shared/Reports/Usage"
    assert path.name is None
    assert path.type is None
    assert path.description is None


def test_analytics_path_success_full():
    """Test successful instantiation with all fields."""
    path_data = {
        "path": "/shared/Reports/Usage",
        "name": "Usage Report",
        "type": "Report",
        "description": "Monthly usage statistics."
    }
    path = AnalyticsPath(**path_data)
    assert path.path == "/shared/Reports/Usage"
    assert path.name == "Usage Report"
    assert path.type == "Report"
    assert path.description == "Monthly usage statistics."


def test_analytics_path_missing_required():
    """Test ValidationError when required 'path' field is missing."""
    path_data = {"name": "Usage Report"}
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsPath(**path_data)
    errors = exc_info.value.errors(include_context=False)
    assert len(errors) == 1
    assert errors[0]['type'] == 'missing'
    assert errors[0]['loc'] == ('path',)


def test_analytics_path_incorrect_type():
    """Test ValidationError when 'path' field has incorrect type."""
    path_data = {"path": 123}
    with pytest.raises(ValidationError) as exc_info:
        AnalyticsPath(**path_data)
    assert "Input should be a valid string" in str(exc_info.value)
