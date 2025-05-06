"""Handles interactions with the Alma Holdings API endpoints."""

from typing import TYPE_CHECKING, Optional, Dict, Any, Union, List
import requests
from pydantic import ValidationError

# Assuming models and exceptions are structured as previously discussed
from ..exceptions import AlmaApiError, InvalidInputError
from ..models.holding import Holding

# Use TYPE_CHECKING to avoid circular import issues with the client
if TYPE_CHECKING:
    from ..client import AlmaApiClient  # pragma: no cover


# noinspection PyUnusedLocal,PyProtectedMember
class HoldingsAPI:
    """Provides access to the Holding Records related API endpoints."""

    def __init__(self, client: 'AlmaApiClient'):
        """
        Initializes the HoldingsAPI with an AlmaApiClient instance.

        Args:
            client: An instance of AlmaApiClient.
        """
        self.client = client

    def get_holding(self, mms_id: str, holding_id: str) -> Holding:
        """
        Retrieves a specific Holding record by its ID and parent Bib MMS ID.

        Corresponds to GET /bibs/{mms_id}/holdings/{holding_id}.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the Holding record.

        Returns:
            A Holding object representing the Alma record.

        Raises:
            ValueError: If mms_id or holding_id are empty.
            NotFoundError: If the MMS ID or Holding ID is not found.
            AlmaApiError: For other API or processing errors.
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")
        if not holding_id:
            raise ValueError("Holding ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}"
        headers = {"Accept": "application/json"}  # Prefer JSON
        response: Optional[requests.Response] = None

        try:
            response = self.client._get(endpoint, headers=headers)
            response_data = response.json()
            holding = Holding.model_validate(response_data)
            return holding
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for Holding {holding_id}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate Holding response data for {holding_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Specific HTTP errors (404 etc) handled by client

    def get_bib_holdings(
            self,
            mms_id: str,
            limit: int = 100,
            offset: int = 0
    ) -> List[Holding]:
        """ Retrieves all Holding records associated with a given Bib MMS ID (Refactored Error Handling) """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings"
        params = {"limit": limit, "offset": offset}
        headers = {"Accept": "application/json"}
        response: Optional[requests.Response] = None  # Keep for potential use in specific error messages
        holdings_list = []

        # Make the API call *before* the try block for parsing
        # Let client._get handle HTTP/network errors directly
        response = self.client._get(endpoint, params=params, headers=headers)
        # If we get here, the HTTP call was successful (e.g., 200 OK)

        # Now try to parse the successful response
        try:
            response_data = response.json()

            holdings_data = response_data.get('holding', [])
            if isinstance(holdings_data, dict):  # Handle single result
                holdings_data = [holdings_data]

            for h_data in holdings_data:
                if isinstance(h_data, dict):
                    holdings_list.append(Holding.model_validate(h_data))

            return holdings_list
        # Catch only errors related to processing the response body
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for Bib holdings {mms_id}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate Holding data for Bib {mms_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        except Exception as e:  # Catch-all for other *processing* errors
            raise AlmaApiError(f"An unexpected error occurred processing holdings list for Bib {mms_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e

    def create_holding(
            self,
            mms_id: str,
            holding_record_data: Union[Holding, Dict[str, Any], str]
    ) -> Holding:
        """ Creates a new Holding record (Removed local dict validation) """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings"
        headers = {"Accept": "application/json"}
        payload: Any
        content_type: Optional[str] = None
        request_kwargs: Dict[str, Any] = {}
        response: Optional[requests.Response] = None

        if isinstance(holding_record_data, str):
            payload = holding_record_data.encode()
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(holding_record_data, dict):
            # --- FIX: Remove local validation, pass dict directly ---
            payload = holding_record_data  # Pass dict directly as JSON
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
            # --------------------------------------------------------
        elif isinstance(holding_record_data, Holding):
            payload = holding_record_data.model_dump(mode='json', by_alias=True, exclude_unset=True)
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("holding_record_data must be a Holding object, dictionary, or XML string.")

        try:
            response = self.client._post(endpoint, headers=headers, **request_kwargs)
            response_data = response.json()
            created_holding = Holding.model_validate(response_data)
            return created_holding
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError("Failed to decode JSON response after creating Holding",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after creating Holding: {e}",
                               response=response, url=getattr(response, 'url', None)) from e

    def update_holding(
            self,
            mms_id: str,
            holding_id: str,
            holding_record_data: Union[Holding, Dict[str, Any], str]
    ) -> Holding:
        """
        Updates an existing Holding record in Alma.

        Corresponds to PUT /bibs/{mms_id}/holdings/{holding_id}.

        Requires sending the *complete* Holding record representation for update.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the Holding record to update.
            holding_record_data: The *complete* updated data for the Holding record. Can be:
                                 - A Holding Pydantic object (recommended).
                                 - A dictionary conforming to the Holding JSON structure.
                                 - A string containing valid MARCXML.

        Returns:
            A Holding object representing the updated Alma record.

        Raises:
            ValueError: If mms_id or holding_id are empty.
            NotFoundError: If the MMS ID or Holding ID is not found.
            InvalidInputError: If the input data is invalid according to Alma.
            AlmaApiError: For other API or processing errors.
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")
        if not holding_id:
            raise ValueError("Holding ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}"
        headers = {"Accept": "application/json"}
        payload: Any
        content_type: Optional[str] = None
        request_kwargs: Dict[str, Any] = {}
        response: Optional[requests.Response] = None

        if isinstance(holding_record_data, str):
            payload = holding_record_data.encode()
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(holding_record_data, dict):
            try:
                # Validate structure before sending PUT request
                holding_obj = Holding.model_validate(holding_record_data)
                # Send all fields for PUT
                payload = holding_obj.model_dump(mode='json', by_alias=True)
                content_type = "application/json"
                headers["Content-Type"] = content_type
                request_kwargs = {"json": payload}
            except ValidationError as e:
                raise InvalidInputError(f"Input dictionary failed Holding model validation before update: {e}") from e
        elif isinstance(holding_record_data, Holding):
            # Send all fields for PUT
            payload = holding_record_data.model_dump(mode='json', by_alias=True)
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("holding_record_data must be a Holding object, dictionary, or XML string.")

        try:
            response = self.client._put(endpoint, headers=headers, **request_kwargs)
            response_data = response.json()
            updated_holding = Holding.model_validate(response_data)
            return updated_holding
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response after updating Holding {holding_id}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after updating Holding {holding_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Other errors handled by client

    def delete_holding(self, mms_id: str, holding_id: str) -> None:
        """
        Deletes a Holding record from Alma.

        Corresponds to DELETE /bibs/{mms_id}/holdings/{holding_id}.

        Warning: This action is permanent. Holdings with attached items usually cannot be deleted.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the Holding record to delete.

        Returns:
            None on successful deletion (HTTP 204).

        Raises:
            ValueError: If mms_id or holding_id are empty.
            NotFoundError: If the MMS ID or Holding ID is not found.
            AlmaApiError: For other API errors (e.g., permissions, holding has items).
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")
        if not holding_id:
            raise ValueError("Holding ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}"
        response: Optional[requests.Response] = None  # Initialize for potential use in error message

        try:
            # Client._delete handles 204 response or raises error otherwise
            response = self.client._delete(endpoint)  # Assign response in case needed by error handler
            return  # Return None on success
        except AlmaApiError as e:
            # Re-raise specific errors or the general one caught by the client
            raise e
