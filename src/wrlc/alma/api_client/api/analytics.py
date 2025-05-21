# src/alma_api_client/api/analytics.py
"""Handles interactions with the Alma Analytics API endpoints."""

import warnings
from typing import TYPE_CHECKING, Optional, Dict, List, Any
import requests
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
    """Provides access to the Analytics related API endpoints."""

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

        Args:
            xml_data: The raw XML bytes response body.

        Returns:
            A dictionary structured for the AnalyticsReportResults model.

        Raises:
            AlmaApiError: If parsing fails significantly or essential data is missing.
        """
        try:
            data = xmltodict.parse(xml_data, process_namespaces=True,
                                   namespaces={'urn:schemas-microsoft-com:xml-analysis:rowset': None})

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
                parsed['IsFinished'] = is_finished_str  # Model alias
            else:
                raise AlmaApiError("Missing 'IsFinished' flag in <QueryResult> after parsing XML response.")

            if token_val is not None:
                if isinstance(token_val, dict) and '#text' in token_val:
                    parsed['ResumptionToken'] = token_val.get('#text')  # Model alias
                elif isinstance(token_val, str):
                    parsed['ResumptionToken'] = token_val

            # Extract Rows and Schema from QueryResult.ResultXml.rowset
            result_xml_node = query_result.get('ResultXml', {})
            rowset_node = result_xml_node.get('rowset', {})  # Namespace was stripped by xmltodict options

            rows_data = rowset_node.get('Row', [])
            if not isinstance(rows_data, list):
                rows_data = [rows_data] if rows_data else []

            parsed_rows = []
            for row in rows_data:
                if not isinstance(row, dict):
                    continue
                row_dict = {}
                for k, v in row.items():
                    if k.startswith('Column'):  # Process only column elements
                        row_dict[k] = v.get('#text') if isinstance(v, dict) else v
                parsed_rows.append(row_dict)
            parsed['rows'] = parsed_rows  # Model field name

            # Extract Columns from schema within rowset
            parsed_columns = []
            schema_node = rowset_node.get('xsd:schema')  # Check for prefixed schema tag

            if schema_node and isinstance(schema_node, dict):
                complex_type_node = schema_node.get('xsd:complexType')
                # Handle if complexType is a list (e.g. multiple complexType definitions)
                if isinstance(complex_type_node, list):
                    complex_type_node = next(
                        (ct for ct in complex_type_node if isinstance(ct, dict) and ct.get('@name') == 'Row'), None)

                if complex_type_node and isinstance(complex_type_node, dict) and complex_type_node.get(
                        '@name') == 'Row':
                    sequence_node = complex_type_node.get('xsd:sequence')
                    if sequence_node and isinstance(sequence_node, dict):
                        elements = sequence_node.get('xsd:element', [])
                        if not isinstance(elements, list):
                            elements = [elements] if elements else []

                        for elem in elements:
                            if isinstance(elem, dict):
                                col_name = elem.get('@saw-sql:columnHeading', elem.get('@name'))
                                col_type = elem.get('@type')
                                if col_name:
                                    parsed_columns.append({"name": col_name, "data_type": col_type})
            parsed['columns'] = parsed_columns  # Model field name

            # Extract QueryPath (if it exists, likely under QueryResult)
            query_path_val = query_result.get('QueryPath')
            if query_path_val is not None:
                if isinstance(query_path_val, dict) and '#text' in query_path_val:
                    parsed['QueryPath'] = query_path_val.get('#text')  # Model alias
                elif isinstance(query_path_val, str):
                    parsed['QueryPath'] = query_path_val

            # Extract JobID (if it exists, likely under QueryResult)
            job_id_val = query_result.get('JobID')
            if job_id_val is not None:
                if isinstance(job_id_val, dict) and '#text' in job_id_val:
                    parsed['JobID'] = job_id_val.get('#text')  # Model alias
                elif isinstance(job_id_val, str):
                    parsed['JobID'] = job_id_val

            return parsed

        except ExpatError as e:
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

        headers = {"Accept": "*/*"}  # Request any content type, then parse based on response
        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")
        report_data_for_model: Dict[str, Any]

        try:
            if "application/json" in content_type:
                raw_response_data = response.json()
                container = None
                if 'QueryResult' in raw_response_data and isinstance(raw_response_data['QueryResult'], dict):
                    container = raw_response_data['QueryResult']
                elif 'Report' in raw_response_data and isinstance(raw_response_data['Report'],
                                                                  dict):  # Check for 'Report' as well
                    container = raw_response_data['Report']
                else:
                    container = raw_response_data

                report_data_for_model = {}

                is_finished_val = container.get('IsFinished')
                if is_finished_val is None and container is not raw_response_data:
                    is_finished_val = raw_response_data.get('IsFinished')
                if is_finished_val is None:
                    raise AlmaApiError("Missing 'IsFinished' flag in JSON response.")
                report_data_for_model['IsFinished'] = is_finished_val

                res_token = container.get('ResumptionToken')
                if res_token is None and container is not raw_response_data:
                    res_token = raw_response_data.get('ResumptionToken')
                if res_token is not None:
                    report_data_for_model['ResumptionToken'] = res_token

                rowset = None
                result_xml_container = container.get('ResultXml')  # ResultXml might be a key in the JSON
                if result_xml_container and isinstance(result_xml_container, dict):
                    rowset = result_xml_container.get('rowset')
                elif 'rowset' in container:  # rowset might be directly under container
                    rowset = container.get('rowset')

                if rowset and isinstance(rowset, dict):
                    rows_data = rowset.get('Row', [])
                    if not isinstance(rows_data, list):
                        rows_data = [rows_data] if rows_data else []
                    report_data_for_model['rows'] = rows_data

                    columns_list = []
                    # Schema might be under ResultXml or directly under container/rowset in JSON
                    schema_container = result_xml_container if result_xml_container and isinstance(result_xml_container,
                                                                                                   dict) else rowset
                    if not schema_container:  # Fallback to container if still not found
                        schema_container = container

                    schema = schema_container.get('xsd:schema',
                                                  schema_container.get('schema'))  # Try with and without prefix
                    if schema and isinstance(schema, dict):
                        try:
                            complex_type = schema.get('complexType', {})
                            elements_container = complex_type.get('sequence', {})
                            elements = elements_container.get('element', [])

                            if not isinstance(elements, list):
                                elements = [elements] if elements else []
                            for elem in elements:
                                if isinstance(elem, dict):
                                    # In JSON, attributes are often prefixed with '@' by xmltodict if converted
                                    col_name = elem.get('@saw-sql:columnHeading', elem.get('saw-sql:columnHeading',
                                                                                           elem.get('@name',
                                                                                                    elem.get('name'))))
                                    col_type = elem.get('@type', elem.get('type'))
                                    if col_name:
                                        columns_list.append({"name": col_name, "data_type": col_type})
                        except Exception:
                            pass
                    report_data_for_model['columns'] = columns_list
                else:
                    report_data_for_model.setdefault('rows', [])
                    report_data_for_model.setdefault('columns', [])

                query_path_val = container.get('QueryPath')
                if query_path_val is None and container is not raw_response_data:
                    query_path_val = raw_response_data.get('QueryPath')
                if query_path_val is not None:
                    report_data_for_model['QueryPath'] = query_path_val

                job_id_val = container.get('JobID')
                if job_id_val is None and container is not raw_response_data:
                    job_id_val = raw_response_data.get('JobID')
                if job_id_val is not None:
                    report_data_for_model['JobID'] = job_id_val

            elif "xml" in content_type:
                warnings.warn("Received XML response for Analytics report. Parsing may be less accurate than JSON. "
                              "Consider adjusting request headers or checking API capabilities.", UserWarning)
                report_data_for_model = self._parse_analytics_xml_results(response.content)
            else:
                raise AlmaApiError(f"Unexpected Content-Type received: {content_type}", response=response,
                                   url=response.url)

            results = AnalyticsReportResults.model_validate(report_data_for_model)
            if results.query_path is None:  # Ensure query_path is set from the input if not in response
                results.query_path = path
            return results

        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response: {e}", response=response, url=response.url) from e
        except ExpatError as e:  # This would be raised from _parse_analytics_xml_results
            raise AlmaApiError(f"Failed to parse XML response: {e}", response=response, url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate API response against model: {e}", response=response,
                               url=response.url) from e
        except AlmaApiError:  # Re-raise AlmaApiErrors from _parse_analytics_xml_results
            raise
        except Exception as e:
            raise AlmaApiError(f"An unexpected error occurred processing the report response: {e}", response=response,
                               url=response.url) from e

    # --- UPDATED list_paths method ---
    def list_paths(self, folder_path: Optional[str] = None) -> List[AnalyticsPath]:
        """ Lists available paths, removed conditional validation """
        endpoint = "/analytics/paths"
        params = {"path": folder_path} if folder_path else {}
        headers = {"Accept": "application/json, application/xml;q=0.9"}  # Prefer JSON

        response = self.client._get(endpoint, params=params, headers=headers)
        content_type = response.headers.get("Content-Type", "")
        paths_list: List[AnalyticsPath] = []

        try:
            if "application/json" in content_type:
                data = response.json()
                # Alma often wraps lists: {"path": [...]} or {"AnalyticsPathsResult": {"path": [...]}}
                path_items_data = data.get("path", data.get("AnalyticsPathsResult", {}).get("path", []))

                if not isinstance(path_items_data, list):
                    path_items_data = [path_items_data] if path_items_data else []

                for item in path_items_data:
                    if isinstance(item, str):  # Simple path string
                        paths_list.append(AnalyticsPath(path=item))
                    elif isinstance(item, dict):  # Dictionary with attributes
                        # xmltodict often prefixes attributes with '@', remove if present for model validation
                        path_detail = {k.lstrip('@'): v for k, v in item.items()}
                        paths_list.append(AnalyticsPath.model_validate(path_detail))

            elif "xml" in content_type:
                data = xmltodict.parse(response.content)
                path_items_data = data.get("AnalyticsPathsResult", {}).get("path", [])
                if not isinstance(path_items_data, list):
                    path_items_data = [path_items_data] if path_items_data else []

                for item in path_items_data:
                    if isinstance(item, dict):
                        # xmltodict prefixes attributes with '@'
                        path_detail = {k.lstrip('@'): v for k, v in item.items()}
                        paths_list.append(AnalyticsPath.model_validate(path_detail))
                    elif isinstance(item, str):  # Should not happen if XML is structured with attributes
                        paths_list.append(AnalyticsPath(path=item))
            else:
                raise AlmaApiError(f"Unexpected Content-Type for paths: {content_type}", response=response,
                                   url=response.url)
            return paths_list

        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for paths: {e}", response=response,
                               url=response.url) from e
        except ExpatError as e:
            raise AlmaApiError(f"Failed to parse XML response for paths: {e}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate paths data: {e}", response=response, url=response.url) from e
        except AlmaApiError:  # Re-raise
            raise
        except Exception as e:
            raise AlmaApiError(f"An unexpected error occurred processing paths response: {e}", response=response,
                               url=response.url) from e
