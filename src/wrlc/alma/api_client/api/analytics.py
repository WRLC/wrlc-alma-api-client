# src/wrlc/alma/api_client/api/analytics.py
"""Handles interactions with the Alma Analytics API endpoints."""

# import warnings # No longer needed for the XML parsing warning
from typing import TYPE_CHECKING, Optional, Dict, List, Any
import xmltodict
from xml.parsers.expat import ExpatError
from pydantic import ValidationError
from wrlc.alma.api_client.exceptions import AlmaApiError
from wrlc.alma.api_client.models.analytics import AnalyticsReportResults, AnalyticsPath

# Use TYPE_CHECKING to avoid circular import issues with the client
if TYPE_CHECKING:
    from ..client import AlmaApiClient  # pragma: no cover


# noinspection PyMethodMayBeStatic,PyUnusedLocal,PyProtectedMember,PyBroadException,PyUnreachableCode,PyArgumentList
class AnalyticsAPI:
    """Provides access to the Analytics related API endpoints, focusing on XML responses."""

    def __init__(self, client: 'AlmaApiClient'):
        """
        Initializes the AnalyticsAPI with an AlmaApiClient instance.

        Args:
            client: An instance of AlmaApiClient.
        """
        self.client = client

    def _parse_analytics_xml_results(self, xml_data: bytes) -> Dict[str, Any]:
        """
        Parses the complex Alma Analytics XML report result into a dictionary
        approximating the structure needed by the AnalyticsReportResults model.
        Rows will have keys corresponding to actual column headings from the schema.

        Args:
            xml_data: The raw XML bytes response body.

        Returns:
            A dictionary structured for the AnalyticsReportResults model.

        Raises:
            AlmaApiError: If parsing fails significantly or essential data is missing.
        """
        try:
            data = xmltodict.parse(
                xml_data,
                process_namespaces=True,
                namespaces={
                    'urn:schemas-microsoft-com:xml-analysis:rowset': None,
                    'http://www.w3.org/2001/XMLSchema': None,  # Add for xsd:* elements
                    'urn:saw-sql': None  # Add for saw-sql:* attributes
                }
            )

            report_node = data.get('report', {})
            if not report_node:
                raise AlmaApiError("Missing <report> root element in XML response.")

            query_result = report_node.get('QueryResult', {})
            if not query_result:
                raise AlmaApiError("Missing <QueryResult> element in XML response.")

            parsed: Dict[str, Any] = {}

            # Extract ResumptionToken and IsFinished from QueryResult
            token_val = query_result.get('ResumptionToken')
            is_finished_val = query_result.get('IsFinished')

            is_finished_str: Optional[str] = None
            if isinstance(is_finished_val, dict) and '#text' in is_finished_val:
                is_finished_str = is_finished_val.get('#text')
            elif isinstance(is_finished_val, str):
                is_finished_str = is_finished_val

            if is_finished_str is not None:
                parsed['IsFinished'] = is_finished_str
            else:
                raise AlmaApiError("Missing 'IsFinished' flag in <QueryResult> after parsing XML response.")

            if token_val is not None:
                if isinstance(token_val, dict) and '#text' in token_val:
                    parsed['ResumptionToken'] = token_val.get('#text')
                elif isinstance(token_val, str):
                    parsed['ResumptionToken'] = token_val

            result_xml_node = query_result.get('ResultXml', {})
            rowset_node = result_xml_node.get('rowset', {})

            # 1. Extract Columns and build a mapping
            parsed_columns_for_model = []
            column_xml_tag_to_heading_map: Dict[str, str] = {}

            # Use non-prefixed 'schema' tag due to namespace mapping
            schema_node = rowset_node.get('schema')
            if schema_node and isinstance(schema_node, dict):
                # Use non-prefixed 'complexType'
                complex_type_node = schema_node.get('complexType')
                if isinstance(complex_type_node, list):
                    complex_type_node = next(
                        (ct for ct in complex_type_node if isinstance(ct, dict) and ct.get('@name') == 'Row'), None)

                if complex_type_node and isinstance(complex_type_node, dict) and complex_type_node.get(
                        '@name') == 'Row':
                    # Use non-prefixed 'sequence'
                    sequence_node = complex_type_node.get('sequence')
                    if sequence_node and isinstance(sequence_node, dict):
                        # Use non-prefixed 'element'
                        elements = sequence_node.get('element', [])
                        if not isinstance(elements, list):
                            elements = [elements] if elements else []

                        for elem in elements:
                            if isinstance(elem, dict):
                                xml_tag_name = elem.get('@name')
                                # Use non-prefixed '@columnHeading' for the attribute
                                actual_heading = elem.get('@columnHeading')
                                col_type = elem.get('@type')

                                if xml_tag_name and actual_heading:
                                    column_xml_tag_to_heading_map[xml_tag_name] = actual_heading
                                    parsed_columns_for_model.append({"name": actual_heading, "data_type": col_type})
                                elif xml_tag_name:
                                    column_xml_tag_to_heading_map[xml_tag_name] = xml_tag_name
                                    parsed_columns_for_model.append({"name": xml_tag_name, "data_type": col_type})
            parsed['columns'] = parsed_columns_for_model

            # 2. Parse Rows using the column_xml_tag_to_heading_map
            # This part should now work correctly if the map is populated
            parsed_rows_with_actual_headings = []
            rows_data = rowset_node.get('Row', [])
            if not isinstance(rows_data, list):
                rows_data = [rows_data] if rows_data else []

            for row_item_dict in rows_data:
                if not isinstance(row_item_dict, dict):
                    continue
                transformed_row: Dict[str, Any] = {}
                for xml_key, value_container in row_item_dict.items():
                    actual_value = value_container.get('#text') if isinstance(value_container,
                                                                              dict) else value_container
                    new_key = column_xml_tag_to_heading_map.get(xml_key, xml_key)
                    transformed_row[new_key] = actual_value
                parsed_rows_with_actual_headings.append(transformed_row)

            parsed['rows'] = parsed_rows_with_actual_headings

            # ... (rest of the method for QueryPath, JobID, and error handling) ...
            query_path_val = query_result.get('QueryPath')
            if query_path_val is not None:
                if isinstance(query_path_val, dict) and '#text' in query_path_val:
                    parsed['QueryPath'] = query_path_val.get('#text')
                elif isinstance(query_path_val, str):
                    parsed['QueryPath'] = query_path_val

            job_id_val = query_result.get('JobID')
            if job_id_val is not None:
                if isinstance(job_id_val, dict) and '#text' in job_id_val:
                    parsed['JobID'] = job_id_val.get('#text')
                elif isinstance(job_id_val, str):
                    parsed['JobID'] = job_id_val

            return parsed

        except ExpatError as e:
            raise AlmaApiError(f"Failed to parse Analytics XML response: {e}",
                               response=getattr(e, 'response', None)) from e
        except Exception as e:
            raise AlmaApiError(f"Error processing Analytics XML structure: {e}") from e

    def get_report(
            self,
            path: str,
            limit: int = 1000,
            column_names: bool = True,  # This Alma param might affect XML structure
            resumption_token: Optional[str] = None,
            filter_xml: Optional[str] = None
    ) -> AnalyticsReportResults:
        """
        Retrieves an Analytics report from Alma, expecting an XML response.
        """
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

        headers = {"Accept": "application/xml"}  # Explicitly request XML
        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")

        try:
            if "xml" in content_type.lower():  # Check for XML content type
                report_data_for_model = self._parse_analytics_xml_results(response.content)
            else:
                # Handle unexpected content type, though we requested XML
                raise AlmaApiError(
                    f"Unexpected Content-Type received: {content_type}. Expected XML.",
                    response=response,
                    url=response.url
                )

            results = AnalyticsReportResults.model_validate(report_data_for_model)
            if results.query_path is None:
                results.query_path = path
            return results

        except ExpatError as e:
            raise AlmaApiError(f"Failed to parse Analytics XML response: {e}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate API response against model: {e}", response=response,
                               url=response.url) from e
        except AlmaApiError:  # Re-raise AlmaApiErrors from _parse_analytics_xml_results or other checks
            raise
        except Exception as e:  # pylint: disable=broad-except
            raise AlmaApiError(f"An unexpected error occurred processing the report response: {e}", response=response,
                               url=response.url) from e

    def list_paths(self, folder_path: Optional[str] = None) -> List[AnalyticsPath]:
        """
        Lists available Analytics paths, expecting an XML response.
        """
        endpoint = "/analytics/paths"
        params = {"path": folder_path} if folder_path else {}
        headers = {"Accept": "application/xml"}  # Explicitly request XML

        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")
        paths_list: List[AnalyticsPath] = []

        try:
            if "xml" in content_type.lower():  # Check for XML content type
                data = xmltodict.parse(response.content)
                # Expected structure: <AnalyticsPathsResult><path .../><path .../></AnalyticsPathsResult>
                path_items_data = data.get("AnalyticsPathsResult", {}).get("path", [])
                if not isinstance(path_items_data, list):
                    path_items_data = [path_items_data] if path_items_data else []

                for item in path_items_data:
                    if isinstance(item, dict):
                        # xmltodict prefixes attributes with '@', remove for model validation
                        path_detail = {k.lstrip('@'): v for k, v in item.items()}
                        paths_list.append(AnalyticsPath.model_validate(path_detail))
                    # Simple string paths are less likely in structured XML but handle defensively
                    elif isinstance(item, str):
                        paths_list.append(AnalyticsPath(path=item))
            else:
                # Handle unexpected content type
                raise AlmaApiError(
                    f"Unexpected Content-Type for paths: {content_type}. Expected XML.",
                    response=response,
                    url=response.url
                )
            return paths_list

        except ExpatError as e:
            raise AlmaApiError(f"Failed to parse XML response for paths: {e}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate paths data: {e}", response=response, url=response.url) from e
        except AlmaApiError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            raise AlmaApiError(f"An unexpected error occurred processing paths response: {e}", response=response,
                               url=response.url) from e
