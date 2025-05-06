"""Alma API Client for Python."""

import requests
from typing import Optional, Dict, Any, Union
import importlib.metadata

from .exceptions import (
    AlmaApiError,
    AuthenticationError)

try:
    from .api.analytics import AnalyticsAPI
except ImportError:
    class AnalyticsAPI:
        """A placeholder for the Analytics API class."""
        pass
try:
    from .api.bibs import BibsAPI
except ImportError:
    class BibsAPI:
        """A placeholder for the Bibs API class."""
        pass
try:
    from .api.holdings import HoldingsAPI
except ImportError:
    class HoldingsAPI:
        """A placeholder for the Holdings API class."""
        pass
try:
    from .api.items import ItemsAPI
except ImportError:
    class ItemsAPI:
        """A placeholder for the Items API class."""
        pass
try:
    # noinspection PyUnresolvedReferences
    import xmltodict

    XMLTODICT_INSTALLED = True
except ImportError:
    XMLTODICT_INSTALLED = False
try:
    __version__ = importlib.metadata.version("alma-api-client")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

ALMA_REGION_URLS = {
    "NA": "https://api-na.hosted.exlibrisgroup.com",
    "EU": "https://api-eu.hosted.exlibrisgroup.com",
    "APAC": "https://api-ap.hosted.exlibrisgroup.com",
}
ALMA_API_PATH = "/almaws/v1"


# noinspection PyMethodMayBeStatic,PyBroadException,PyArgumentList,PyUnusedLocal,PyUnresolvedReferences
class AlmaApiClient:
    """
    A client for interacting with the Ex Libris Alma REST APIs.

    Handles authentication, request formation, basic error handling,
    and provides access to different API functional areas.
    """

    def __init__(
            self,
            api_key: str,
            region: str,
            base_url: Optional[str] = None,
            session: Optional[requests.Session] = None,
            timeout: int = 30
    ):
        """
        Initializes the Alma API client.

        Args:
            api_key: Your Alma API key.
            region: The Alma region code (e.g., 'NA', 'EU', 'APAC').
                    Used to determine the base API URL unless 'base_url' is provided.
            base_url: Optional. If provided, overrides the URL derived from 'region'.
                      Should be the base domain (e.g., 'https://api-xx.hosted.exlibrisgroup.com').
            session: Optional. A requests.Session object to use for making requests.
                     If None, a new session is created.
            timeout: Optional. Request timeout in seconds. Defaults to 30.
        """
        if not api_key:
            raise ValueError("API key must be provided.")

        self.api_key = api_key
        self.timeout = timeout

        if base_url:
            self.base_api_url = f"{base_url.rstrip('/')}{ALMA_API_PATH}"
        else:
            region_upper = region.upper()
            if region_upper not in ALMA_REGION_URLS:
                raise ValueError(f"Invalid region '{region}'. Valid regions are: {list(ALMA_REGION_URLS.keys())}")
            self.base_api_url = f"{ALMA_REGION_URLS[region_upper]}{ALMA_API_PATH}"

        self.session = session or requests.Session()
        self.session.headers.update(self._get_default_headers())

        self.analytics = AnalyticsAPI(self) if AnalyticsAPI is not None else None
        self.bibs = BibsAPI(self) if BibsAPI is not None else None
        self.holdings = HoldingsAPI(self) if HoldingsAPI is not None else None
        self.items = ItemsAPI(self) if ItemsAPI is not None else None

    def _get_default_headers(self) -> Dict[str, str]:
        """Returns the default headers for API requests."""
        return {
            "Authorization": f"apikey {self.api_key}",
            "Accept": "application/json, application/xml;q=0.9",
            "User-Agent": f"alma-api-client-py/{__version__}"
        }

    def _request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Union[str, bytes]] = None,
            json: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            stream: bool = False
    ) -> requests.Response:
        """ Internal method to make HTTP requests to the Alma API. """
        full_url = f"{self.base_api_url}{endpoint}"
        # --- FIX 1: Use dict() for copy ---
        request_headers = dict(self.session.headers)  # Create copy using dict()
        # --- End FIX 1 ---
        if headers:
            request_headers.update(headers)

        # Content-Type logic remains the same
        if data is not None and 'Content-Type' not in request_headers:
            content_type = "application/xml"
            if isinstance(data, str) and data.strip().startswith('{'):
                content_type = "application/json"
            request_headers['Content-Type'] = content_type
        elif json is not None and 'Content-Type' not in request_headers:
            request_headers['Content-Type'] = 'application/json'

        try:
            response = self.session.request(
                method=method.upper(),
                url=full_url,
                params=params,
                data=data,
                json=json,
                headers=request_headers,
                timeout=self.timeout,
                stream=stream
            )
            self._handle_response_errors(response)
            return response
        # Exception handling remains the same
        except requests.exceptions.Timeout as e:
            raise AlmaApiError(f"Request timed out after {self.timeout} seconds: {e}", url=full_url) from e
        except requests.exceptions.RequestException as e:
            raise AlmaApiError(f"Network error during API request: {e}", url=full_url) from e

    def _handle_response_errors(self, response: requests.Response):
        """Checks response status code and raises appropriate custom exceptions."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code
            url = response.url
            response_body = None
            try:
                response_body = response.text
            except Exception:
                pass

            error_detail = ""
            try:
                content_type = response.headers.get('Content-Type', '').lower()
                if response_body and "application/json" in content_type:
                    # JSON handling remains the same...
                    res_json = response.json()  # Might re-raise JSONDecodeError if body invalid
                    errors = res_json.get("errorList", {}).get("error", [])
                    if not isinstance(errors, list):
                        errors = [errors]
                    if errors and isinstance(errors[0], dict) and "errorMessage" in errors[0]:
                        # Use .get() here too just for consistency, though key check exists
                        error_detail = f" Detail: {errors[0].get('errorMessage', '')}"

                elif response_body and "xml" in content_type:
                    if XMLTODICT_INSTALLED:
                        try:
                            err_data = xmltodict.parse(response_body)
                            # Navigate potential structures to find the error list/object
                            error_list_container = err_data.get("web_service_result", {}).get("errorList", {})
                            if not error_list_container:
                                error_list_container = err_data.get("errorList", {})

                            errors = error_list_container.get("error", [])
                            if not isinstance(errors, list):
                                errors = [errors]

                            # Check list has content AND first item is dict before accessing
                            if errors and isinstance(errors[0], dict):
                                error_dict = errors[0]  # Assign to variable first
                                # --- FIX: Use .get() for both accesses ---
                                err_msg = error_dict.get("errorMessage")  # Use .get() for 'errorMessage'
                                # Handle xmltodict's #text ONLY if errorMessage wasn't found
                                if err_msg is None:
                                    err_msg = error_dict.get('#text')  # Use .get() for '#text'
                                # --- End FIX ---
                                if err_msg:
                                    error_detail = f" Detail: {err_msg}"
                        except Exception:  # Catch errors during XML parsing/access
                            error_detail = " (Failed to extract detail from XML response)"
                    else:
                        error_detail = " (XML response received, but xmltodict not installed to parse details)"

            except Exception:  # Catch other errors during detail extraction
                error_detail = " (Failed to extract detail from response body)"
                pass

            # Construct final message (logic remains the same)
            base_message = str(e)
            if url and url in base_message:
                base_message = base_message.split(url)[0].strip()
            display_url = url if not url or len(url) < 100 else url[:97] + "..."
            prefix = ""
            if status_code:
                prefix += f"HTTP {status_code} "
            if url:
                prefix += f"for URL {display_url} "
            detail_str = f" Detail: {error_detail}" if error_detail else ""
            full_message = f"{prefix}: {base_message}{detail_str}"

            # Raise specific errors (logic remains the same)
            if status_code in (401, 403):
                raise AuthenticationError(message=full_message, status_code=status_code, response=response,
                                          url=url) from e
            # ... other specific error raises ...
            else:
                raise AlmaApiError(message=full_message, status_code=status_code, response=response, url=url) from e

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """Internal GET request helper."""
        return self._request("GET", endpoint, params=params, **kwargs)

    def _post(self, endpoint: str, data=None, json=None, params=None, **kwargs) -> requests.Response:
        """Internal POST request helper."""
        return self._request("POST", endpoint, params=params, data=data, json=json, **kwargs)

    def _put(self, endpoint: str, data=None, json=None, params=None, **kwargs) -> requests.Response:
        """Internal PUT request helper."""
        return self._request("PUT", endpoint, params=params, data=data, json=json, **kwargs)

    def _delete(self, endpoint: str, params=None, **kwargs) -> requests.Response:
        """Internal DELETE request helper."""
        return self._request("DELETE", endpoint, params=params, **kwargs)
