"""Handles interactions with the Alma Item API endpoints."""

from typing import TYPE_CHECKING, Optional, Dict, Any, Union, List
import requests
from pydantic import ValidationError
from wrlc_alma_api_client.exceptions import AlmaApiError
from wrlc_alma_api_client.models.item import Item

# Use TYPE_CHECKING to avoid circular import issues with the client
if TYPE_CHECKING:
    from ..client import AlmaApiClient  # pragma: no cover


# noinspection PyUnusedLocal,PyProtectedMember
class ItemsAPI:
    """Provides access to the Item Records related API endpoints."""

    def __init__(self, client: 'AlmaApiClient'):
        """
        Initializes the ItemsAPI with an AlmaApiClient instance.

        Args:
            client: An instance of AlmaApiClient.
        """
        self.client = client

    def get_item(self, mms_id: str, holding_id: str, item_pid: str) -> Item:
        """
        Retrieves a specific Item record by its PID and parent identifiers.

        Corresponds to GET /bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the parent Holding record.
            item_pid: The PID (Process ID) of the Item record.

        Returns:
            An Item object representing the Alma record.

        Raises:
            ValueError: If any ID is empty.
            NotFoundError: If the Bib, Holding, or Item ID is not found.
            AlmaApiError: For other API or processing errors.
        """
        if not all([mms_id, holding_id, item_pid]):
            raise ValueError("MMS ID, Holding ID, and Item PID must all be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}"
        headers = {"Accept": "application/json"}  # Prefer JSON
        response: Optional[requests.Response] = None

        try:
            response = self.client._get(endpoint, headers=headers)
            response_data = response.json()
            item = Item.model_validate(response_data)
            return item
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for Item {item_pid}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate Item response data for {item_pid}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Specific HTTP errors (404 etc) handled by client

    def get_holding_items(
            self,
            mms_id: str,
            holding_id: str,
            limit: int = 100,
            offset: int = 0
    ) -> List[Item]:
        """
        Retrieves all Item records associated with a given Holding ID and Bib MMS ID.

        Corresponds to GET /bibs/{mms_id}/holdings/{holding_id}/items.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the parent Holding record.
            limit: Maximum number of records to return (default 100).
            offset: Record number to start from (default 0 for pagination).

        Returns:
            A list of Item objects. Returns an empty list if none are found.

        Raises:
            ValueError: If mms_id or holding_id are empty.
            AlmaApiError: For API or processing errors.
        """
        if not all([mms_id, holding_id]):
            raise ValueError("MMS ID and Holding ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}/items"
        params = {"limit": limit, "offset": offset}
        headers = {"Accept": "application/json"}  # Prefer JSON
        response: Optional[requests.Response] = None
        items_list = []

        # Make the API call *before* the try block for parsing
        response = self.client._get(endpoint, params=params, headers=headers)
        # If we get here, the HTTP call was successful (e.g., 200 OK)

        # Now try to parse the successful response
        try:
            response_data = response.json()

            # Alma often wraps lists: {"item": [...], "total_record_count": X}
            items_data = response_data.get('item', [])
            # Handle case where API might return single object instead of list if count=1
            if isinstance(items_data, dict):
                items_data = [items_data]

            for i_data in items_data:
                if isinstance(i_data, dict):
                    # Validate each item record individually
                    items_list.append(Item.model_validate(i_data))

            return items_list
        # Catch only errors related to processing the response body
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for Holding items {holding_id}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            # This might catch errors validating individual items
            raise AlmaApiError(f"Failed to validate Item data for Holding {holding_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        except Exception as e:  # Catch-all for other *processing* errors
            raise AlmaApiError(f"An unexpected error occurred processing items list for Holding {holding_id}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e

    def create_item(
            self,
            mms_id: str,
            holding_id: str,
            item_record_data: Union[Item, Dict[str, Any], str]
    ) -> Item:
        """
        Creates a new Item record under a specific Holding record.

        Corresponds to POST /bibs/{mms_id}/holdings/{holding_id}/items.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the parent Holding record.
            item_record_data: The data for the new Item record. Can be:
                              - An Item Pydantic object.
                              - A dictionary conforming to the Item JSON structure.
                              - A string containing valid MARCXML (less common for items).

        Returns:
            An Item object representing the newly created Alma record.

        Raises:
            ValueError: If mms_id or holding_id are empty.
            InvalidInputError: If the input data is invalid according to Alma.
            NotFoundError: If the parent MMS ID or Holding ID is not found.
            AlmaApiError: For other API or processing errors.
        """
        if not all([mms_id, holding_id]):
            raise ValueError("MMS ID and Holding ID must be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}/items"
        headers = {"Accept": "application/json"}
        payload: Any
        content_type: Optional[str] = None
        request_kwargs: Dict[str, Any] = {}
        response: Optional[requests.Response] = None

        if isinstance(item_record_data, str):
            payload = item_record_data.encode()
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(item_record_data, dict):
            # Pass dict directly, rely on API validation
            payload = item_record_data
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        elif isinstance(item_record_data, Item):
            # Exclude system-generated fields? Check API docs. Assume exclude_unset for now.
            # Exclude top-level link?
            payload = item_record_data.model_dump(mode='json', by_alias=True, exclude_unset=True, exclude={'link'})
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("item_record_data must be an Item object, dictionary, or XML string.")

        try:
            response = self.client._post(endpoint, headers=headers, **request_kwargs)
            response_data = response.json()
            created_item = Item.model_validate(response_data)
            return created_item
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError("Failed to decode JSON response after creating Item",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after creating Item: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Other errors (400 InvalidInputError, 404 NotFoundError for bib/holding, etc.) handled by client

    def update_item(
            self,
            mms_id: str,
            holding_id: str,
            item_pid: str,
            item_record_data: Union[Item, Dict[str, Any], str]
    ) -> Item:
        """
        Updates an existing Item record in Alma.

        Corresponds to PUT /bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}.

        Requires sending the *complete* Item record representation for update.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the parent Holding record.
            item_pid: The PID of the Item record to update.
            item_record_data: The *complete* updated data for the Item record. Can be:
                              - An Item Pydantic object (recommended).
                              - A dictionary conforming to the Item JSON structure.
                              - A string containing valid MARCXML (less common).

        Returns:
            An Item object representing the updated Alma record.

        Raises:
            ValueError: If any ID is empty.
            NotFoundError: If the Bib, Holding, or Item ID is not found.
            InvalidInputError: If the input data is invalid according to Alma.
            AlmaApiError: For other API or processing errors.
        """
        if not all([mms_id, holding_id, item_pid]):
            raise ValueError("MMS ID, Holding ID, and Item PID must all be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}"
        headers = {"Accept": "application/json"}
        payload: Any
        content_type: Optional[str] = None
        request_kwargs: Dict[str, Any] = {}
        response: Optional[requests.Response] = None

        if isinstance(item_record_data, str):
            payload = item_record_data.encode()
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(item_record_data, dict):
            # Pass dict directly for PUT, ensuring it represents the *complete* record
            payload = item_record_data
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        elif isinstance(item_record_data, Item):
            # Send all fields for PUT (don't exclude unset)
            payload = item_record_data.model_dump(mode='json', by_alias=True)
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("item_record_data must be an Item object, dictionary, or XML string.")

        try:
            response = self.client._put(endpoint, headers=headers, **request_kwargs)
            response_data = response.json()
            updated_item = Item.model_validate(response_data)
            return updated_item
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response after updating Item {item_pid}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after updating Item {item_pid}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Other errors handled by client

    def delete_item(self, mms_id: str, holding_id: str, item_pid: str) -> None:
        """
        Deletes an Item record from Alma.

        Corresponds to DELETE /bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}.

        Warning: This action is permanent. Items involved in processes (loans, requests) usually cannot be deleted.

        Args:
            mms_id: The MMS ID of the parent Bib record.
            holding_id: The ID of the parent Holding record.
            item_pid: The PID of the Item record to delete.

        Returns:
            None on successful deletion (HTTP 204).

        Raises:
            ValueError: If any ID is empty.
            NotFoundError: If the Bib, Holding, or Item ID is not found.
            AlmaApiError: For other API errors (e.g., permissions, item cannot be deleted).
        """
        if not all([mms_id, holding_id, item_pid]):
            raise ValueError("MMS ID, Holding ID, and Item PID must all be provided.")

        endpoint = f"/bibs/{mms_id}/holdings/{holding_id}/items/{item_pid}"
        response: Optional[requests.Response] = None  # Initialize for potential use in error message

        try:
            # Client._delete handles 204 response or raises error otherwise
            response = self.client._delete(endpoint)  # Assign in case needed by error handler
            return  # Return None on success
        except AlmaApiError as e:
            # Re-raise specific errors or the general one caught by the client
            raise e

    def get_item_by_barcode(self, item_barcode: str) -> Item:
        """
        Retrieves a specific Item record by its barcode.

        Corresponds to GET /items?item_barcode={item_barcode}.

        Note: This endpoint retrieves the item directly, without needing MMS ID or Holding ID.

        Args:
            item_barcode: The barcode of the Item record.

        Returns:
            An Item object representing the Alma record.

        Raises:
            ValueError: If item_barcode is empty.
            NotFoundError: If the Item barcode is not found.
            AlmaApiError: For other API or processing errors.
        """
        if not item_barcode:
            raise ValueError("Item barcode must be provided.")

        endpoint = "/items"
        params = {"item_barcode": item_barcode}
        headers = {"Accept": "application/json"}  # Prefer JSON
        response: Optional[requests.Response] = None

        try:
            response = self.client._get(endpoint, params=params, headers=headers)
            response_data = response.json()
            # The response for this endpoint is directly the Item object, not nested
            item = Item.model_validate(response_data)
            return item
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for Item barcode {item_barcode}",
                               response=response, url=getattr(response, 'url', None)) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate Item response data for barcode {item_barcode}: {e}",
                               response=response, url=getattr(response, 'url', None)) from e
        # Specific HTTP errors (404 etc) handled by client._get
