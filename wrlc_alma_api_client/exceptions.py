# src/alma_api_client/exceptions.py
"""Custom Exception classes for the Alma API Client."""
from pyexpat import ExpatError

try:
    # noinspection PyUnresolvedReferences
    import xmltodict

    XMLTODICT_INSTALLED = True
except ImportError:
    XMLTODICT_INSTALLED = False

# Attempt to import requests components for type hinting if available
try:
    import requests
except ImportError:
    requests = None  # type: ignore # Allow code to run if requests not installed during isolated import

from typing import Optional, TYPE_CHECKING
# noinspection PyUnresolvedReferences
from pydantic import ValidationError

# Use TYPE_CHECKING for Response hint to avoid hard dependency cycle potential
if TYPE_CHECKING:
    from requests import Response  # pragma: no cover


# noinspection PyBroadException
class AlmaApiError(Exception):
    """Base class for Alma API client errors."""

    def __init__(
            self,
            message: str = "An unspecified error occurred with the Alma API.",
            status_code: Optional[int] = None,
            response: Optional['Response'] = None,
            url: Optional[str] = None
    ):
        """ Initialize the base Alma API Error. """
        self.status_code = status_code
        self.response = response
        self.url = url
        self.detail = ""  # Store extracted detail separately
        response_body = None

        # Safely attempt to get response body text once
        if response is not None:
            try:
                response_body = response.text
            except Exception:
                # Ignore potential errors reading response body (e.g., if stream consumed)
                pass

        # Try to get more specific error message from Alma response if possible
        if response is not None and response_body:
            try:
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/json" in content_type:
                    # Attempt to parse JSON only if content type matches
                    try:
                        res_json = response.json()  # Use response.json() for potential cached efficiency
                        errors = res_json.get("errorList", {}).get("error", [])
                        if not isinstance(errors, list):
                            errors = [errors]
                        if errors and isinstance(errors[0], dict) and errors[0].get("errorMessage"):
                            self.detail = errors[0]['errorMessage']
                    except requests.exceptions.JSONDecodeError:
                        self.detail = "(Failed to decode JSON response body)"

                elif "xml" in content_type:
                    if XMLTODICT_INSTALLED:
                        try:
                            err_data = xmltodict.parse(response_body)
                            error_list_container = err_data.get("web_service_result", {}).get("errorList", {})
                            if not error_list_container:
                                error_list_container = err_data.get("errorList", {})
                            errors = error_list_container.get("error", [])
                            if not isinstance(errors, list):
                                errors = [errors]

                            if errors:  # Check if errors list is not empty
                                first_error = errors[0]
                                # --- FIX: Handle if first_error is dict OR str ---
                                if isinstance(first_error, dict):
                                    err_msg = first_error.get("errorMessage")
                                    if err_msg is None:
                                        err_msg = first_error.get('#text')
                                    if err_msg:
                                        self.detail = err_msg
                                elif isinstance(first_error, str):
                                    self.detail = first_error  # Use string directly
                                # --- End FIX ---
                        except ExpatError:  # Catch specific XML parsing error
                            self.detail = "(Failed to parse XML response body)"
                        except Exception:  # Catch other potential errors during XML processing
                            self.detail = "(Error processing XML response body)"
                    else:
                        self.detail = " (XML response received, but xmltodict not installed to parse details)"
                # else: detail remains "" for other content types

            except Exception:  # Catch unexpected errors during content-type checks or initial parsing attempts
                # Use a more general fallback message if we couldn't even attempt parsing
                self.detail = "(Failed to extract detail from response body)"
                pass
        elif response is not None and not response_body and response.status_code >= 400:
            # Handle cases where error response might have no body
            self.detail = "(Received error status with empty response body)"

        # Construct the final message (logic remains the same)
        display_url = url if not url or len(url) < 100 else url[:97] + "..."
        prefix = ""
        if status_code:
            prefix += f"HTTP {status_code} "
        if url:
            prefix += f"for URL {display_url} "
        detail_str = f" Detail: {self.detail}" if self.detail else ""
        # Ensure base message isn't duplicated if already in detail (simple check)
        base_message = message
        if self.detail and self.detail in message:
            base_message = ""  # Avoid repeating if detail is already the core message
        elif url and url in message:  # Clean up base message from HTTPError
            base_message = message.split(url)[0].strip()

        full_message = f"{prefix}: {base_message}{detail_str}".strip()
        # Ensure message doesn't end with just ": " if base_message was empty
        if full_message.endswith(": "):
            full_message = full_message[:-2]

        super().__init__(full_message)


class AuthenticationError(AlmaApiError):
    """Raised for authentication errors (401, 403)."""

    def __init__(
            self,
            message: str = "Authentication failed. Check API key and permissions.",
            status_code: Optional[int] = None,
            response: Optional['Response'] = None,
            url: Optional[str] = None
    ):
        super().__init__(message, status_code=status_code, response=response, url=url)


class NotFoundError(AlmaApiError):
    """Raised when a resource is not found (404)."""

    def __init__(
            self,
            message: str = "Resource not found.",
            status_code: int = 404,
            response: Optional['Response'] = None,
            url: Optional[str] = None
    ):
        super().__init__(message, status_code=status_code, response=response, url=url)


class RateLimitError(AlmaApiError):
    """Raised when API rate limits are exceeded (429)."""

    def __init__(
            self,
            message: str = "API rate limit exceeded.",
            status_code: int = 429,
            response: Optional['Response'] = None,
            url: Optional[str] = None
    ):
        super().__init__(message, status_code=status_code, response=response, url=url)


class InvalidInputError(AlmaApiError):
    """Raised for client-side input errors (400)."""

    def __init__(
            self,
            message: str = "Invalid input provided.",
            status_code: int = 400,
            response: Optional['Response'] = None,
            url: Optional[str] = None
    ):
        super().__init__(message, status_code=status_code, response=response, url=url)

# You can add other specific error types here as needed,
# for example, for specific Alma error codes sometimes returned in the body.
# class AlmaLogicError(AlmaApiError):
#     """Raised for specific logical errors reported by Alma within a 200/400 response."""
#     def __init__(self, message, alma_error_code=None, ...)
