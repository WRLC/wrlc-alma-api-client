# src/alma_api_client/api/analytics.py
"""Handles interactions with the Alma Analytics API endpoints."""

import warnings
from typing import TYPE_CHECKING, Optional, Dict, List, Any
import requests  # Ensure requests is imported for exception handling
import xmltodict
from xml.parsers.expat import ExpatError  # <-- FIX: Import ExpatError
from pydantic import ValidationError  # Ensure ValidationError is imported

from ..exceptions import AlmaApiError  # Ensure exceptions are imported
from ..models.analytics import AnalyticsReportResults, AnalyticsPath

# Use TYPE_CHECKING to avoid circular import issues with the client
if TYPE_CHECKING:
    from ..client import AlmaApiClient  # pragma: no cover


# noinspection PyMethodMayBeStatic,PyUnusedLocal,PyProtectedMember,PyBroadException,PyUnreachableCode,PyArgumentList
class AnalyticsAPI:
    """Provides access to the Analytics related API endpoints."""

    def __init__(self, client: 'AlmaApiClient'):
        """
        Initializes the AnalyticsAPI with an AlmaApiClient instance.

        Args:
            client: An instance of AlmaApiClient.
        """
        self.client = client

    # _parse_analytics_xml_results helper remains the same as previously provided
    def _parse_analytics_xml_results(self, xml_data: bytes) -> Dict[str, Any]:
        """
        Parses the complex Alma Analytics XML report result into a dictionary
        approximating the structure needed by the AnalyticsReportResults model.

        Note: This is a simplified parser and might need adjustments based on
              specific report structures or edge cases. Prefer JSON responses.

        Args:
            xml_data: The raw XML bytes response body.

        Returns:
            A dictionary structured for the AnalyticsReportResults model.

        Raises:
            AlmaApiError: If parsing fails significantly.
        """
        try:
            # Use process_namespaces and specific namespace map if needed, or keep simple
            data = xmltodict.parse(xml_data, process_namespaces=True,
                                   namespaces={'urn:schemas-microsoft-com:xml-analysis:rowset': None})

            query_result = data.get('QueryResult', {})
            report_element = query_result.get('ResultXml', {}).get('rowset', {}).get('Report', {})

            # Simplified fallback logic
            if not report_element:
                report_element = query_result.get('ResultXml', {}).get('rowset', {}) or \
                                 query_result.get('ResultXml', {}) or \
                                 query_result

            parsed: Dict[str, Any] = {}

            # Extract ResumptionToken and IsFinished (handle potential dict structure from xmltodict)
            token = query_result.get('ResumptionToken') or report_element.get('ResumptionToken')
            is_finished_val = query_result.get('IsFinished') or report_element.get('IsFinished')

            if isinstance(is_finished_val, dict) and '#text' in is_finished_val:
                is_finished_str = is_finished_val.get('#text')
            elif isinstance(is_finished_val, str):
                is_finished_str = is_finished_val
            else:
                is_finished_str = None  # Or raise if strictly required

            # Pass the key expected by the model (using alias)
            if is_finished_str is not None:
                parsed['IsFinished'] = is_finished_str  # Let model handle bool parsing
            else:
                raise AlmaApiError("Missing 'IsFinished' flag after parsing XML response.")

            if isinstance(token, dict) and '#text' in token:
                parsed['ResumptionToken'] = token.get('#text')
            elif isinstance(token, str):
                parsed['ResumptionToken'] = token

            # Extract Rows
            rows_data = report_element.get('Row', [])
            if not isinstance(rows_data, list):
                rows_data = [rows_data] if rows_data else []

            parsed_rows = []
            for row in rows_data:
                if not isinstance(row, dict):
                    continue
                # Extract values, potentially from '#text' sub-key if attributes exist
                row_dict = {}
                for k, v in row.items():
                    if k.startswith('Column'):
                        row_dict[k] = v.get('#text') if isinstance(v, dict) else v
                parsed_rows.append(row_dict)

            parsed['rows'] = parsed_rows

            # Placeholder/Simplified Column Extraction - Needs improvement for accuracy
            parsed['columns'] = []
            schema = query_result.get('ResultXml', {}).get('xsd:schema') or query_result.get('ResultXml', {}).get(
                'Schema')
            # TODO: Add robust schema parsing here if needed for columns

            parsed['query_path'] = report_element.get('QueryPath')

            return parsed

        except ExpatError as e:  # Catch specific XML parsing error
            raise AlmaApiError(f"Failed to parse Analytics XML response: {e}",
                               response=getattr(e, 'response', None)) from e
        except Exception as e:
            # Catch other potential errors during dict navigation/parsing
            raise AlmaApiError(f"Error processing Analytics XML structure: {e}") from e

    # --- UPDATED get_report method ---
    def get_report(
            self,
            path: str,
            limit: int = 1000,
            column_names: bool = True,
            resumption_token: Optional[str] = None,
            filter_xml: Optional[str] = None
    ) -> AnalyticsReportResults:
        """ Get report results, refactored JSON handling """
        endpoint = "/analytics/reports"
        params: Dict[str, Any] = {
            "path": path,
            "limit": limit,
            "colNames": column_names
        }
        if resumption_token:
            params["token"] = resumption_token
        if filter_xml:
            params["filter"] = filter_xml

        headers = {"Accept": "application/json, application/xml;q=0.9"}
        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")
        report_data_for_model: Dict[str, Any] = {}  # Initialize dict to pass to model

        try:
            if "application/json" in content_type:
                raw_response_data = response.json()
                # Find the main container
                container = None
                if 'QueryResult' in raw_response_data and isinstance(raw_response_data['QueryResult'], dict):
                    container = raw_response_data['QueryResult']
                elif 'Report' in raw_response_data and isinstance(raw_response_data['Report'], dict):
                    container = raw_response_data['Report']
                else:
                    container = raw_response_data  # Assume flat structure

                # Extract fields needed by the model, respecting aliases
                # IsFinished (Required)
                is_finished_val = container.get('IsFinished')
                if is_finished_val is None:
                    is_finished_val = raw_response_data.get('IsFinished')  # Check root
                if is_finished_val is None:
                    raise AlmaApiError("Missing 'IsFinished' flag in JSON response.")
                report_data_for_model['IsFinished'] = is_finished_val  # Use model's alias key

                # ResumptionToken (Optional)
                res_token = container.get('ResumptionToken')
                if res_token is None:
                    res_token = raw_response_data.get('ResumptionToken')  # Check root
                if res_token is not None:
                    report_data_for_model['ResumptionToken'] = res_token  # Use model's alias key

                # Rows and Columns (Potentially nested)
                rowset = None
                result_xml = container.get('ResultXml')
                if result_xml and isinstance(result_xml, dict):
                    rowset = result_xml.get('rowset')
                elif 'rowset' in container:
                    rowset = container.get('rowset')

                if rowset and isinstance(rowset, dict):
                    rows_data = rowset.get('Row', [])
                    if not isinstance(rows_data, list):
                        rows_data = [rows_data] if rows_data else []
                    report_data_for_model['rows'] = rows_data  # Assign rows directly

                    # Column Extraction (Simplified)
                    columns_list = []
                    schema = result_xml.get('xsd:schema') if result_xml else container.get('xsd:schema')  # Find schema
                    if schema and isinstance(schema, dict):
                        try:
                            elements = schema.get('complexType', {}).get('sequence', {}).get('element', [])
                            if not isinstance(elements, list):
                                elements = [elements]
                            for elem in elements:
                                if isinstance(elem, dict):
                                    col_name = elem.get('@saw-sql:columnHeading', elem.get('@name'))
                                    col_type = elem.get('@type')
                                    if col_name:
                                        columns_list.append({"name": col_name, "data_type": col_type})  # Create dicts
                        except Exception:
                            pass  # Ignore schema parsing errors
                    report_data_for_model['columns'] = columns_list  # Assign columns list
                else:
                    report_data_for_model.setdefault('rows', [])
                    report_data_for_model.setdefault('columns', [])

                # Other optional fields
                report_data_for_model['query_path'] = container.get('QueryPath')
                report_data_for_model['job_id'] = container.get('JobID')

            elif "xml" in content_type:
                warnings.warn("Received XML response for Analytics report, parsing may be less accurate than JSON. "
                              "Consider adjusting request headers or checking API capabilities.", UserWarning)
                # Use the XML parser helper (which should raise if IsFinished is missing)
                report_data_for_model = self._parse_analytics_xml_results(response.content)

            else:
                raise AlmaApiError(f"Unexpected Content-Type received: {content_type}", response=response,
                                   url=response.url)

            # Now instantiate the model with the prepared dictionary
            results = AnalyticsReportResults.model_validate(report_data_for_model)
            if results.query_path is None:
                results.query_path = path  # Add path if missing
            return results

        # --- Catch specific parsing/validation errors and wrap them ---
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response: {e}", response=response, url=response.url) from e
        except ExpatError as e:  # Catch XML error specifically if needed after _parse call
            raise AlmaApiError(f"Failed to parse XML response: {e}", response=response, url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate API response against model: {e}", response=response,
                               url=response.url) from e
        except Exception as e:  # Catch any other unexpected errors during processing
            raise AlmaApiError(f"An unexpected error occurred processing the report response: {e}", response=response,
                               url=response.url) from e

    # --- UPDATED list_paths method ---
    def list_paths(self, folder_path: Optional[str] = None) -> List[AnalyticsPath]:
        """ Lists available paths, removed conditional validation """
        endpoint = "/analytics/paths"
        params = {"path": folder_path} if folder_path else {}
        headers = {"Accept": "application/json, application/xml;q=0.9"}

        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")
        paths = []

        try:
            if "application/json" in content_type:
                data = response.json()
                path_list = data.get("path", [])
                if not isinstance(path_list, list):
                    path_list = [path_list]

                for item in path_list:
                    if isinstance(item, str):
                        paths.append(AnalyticsPath(path=item))
                    elif isinstance(item, dict):
                        path_detail = {k.lstrip('@'): v for k, v in item.items()}
                        # --- FIX: Validate directly, let model handle missing 'path' ---
                        paths.append(AnalyticsPath.model_validate(path_detail))

            elif "xml" in content_type:
                data = xmltodict.parse(response.content)
                path_list = data.get("AnalyticsPathsResult", {}).get("path", [])
                if not isinstance(path_list, list):
                    path_list = [path_list]

                for item in path_list:
                    if isinstance(item, dict):
                        path_detail = {k.lstrip('@'): v for k, v in item.items()}
                        # --- FIX: Validate directly, let model handle missing 'path' ---
                        paths.append(AnalyticsPath.model_validate(path_detail))
            else:
                raise AlmaApiError(f"Unexpected Content-Type for paths: {content_type}", response=response,
                                   url=response.url)

            return paths  # Return successful result

        # --- Catch specific errors ---
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for paths: {e}", response=response,
                               url=response.url) from e
        except ExpatError as e:
            raise AlmaApiError(f"Failed to parse XML response for paths: {e}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate paths data: {e}", response=response, url=response.url) from e
        except Exception as e:  # Catch-all for other processing errors
            raise AlmaApiError(f"An unexpected error occurred processing paths response: {e}", response=response,
                               url=response.url) from e
