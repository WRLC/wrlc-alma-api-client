"""Handles interactions with the Alma Bib Records API endpoints."""

import warnings
from typing import TYPE_CHECKING, Optional, Dict, Any, Union
import requests
from pydantic import ValidationError
from wrlc_alma_api_client.exceptions import AlmaApiError, InvalidInputError
from wrlc_alma_api_client.models.bib import Bib

# Use TYPE_CHECKING to avoid circular import issues with the client
if TYPE_CHECKING:
    from ..client import AlmaApiClient  # pragma: no cover


# noinspection PyProtectedMember,PyUnusedLocal
class BibsAPI:
    """Provides access to the Bib Records related API endpoints."""

    def __init__(self, client: 'AlmaApiClient'):
        """
        Initializes the BibsAPI with an AlmaApiClient instance.

        Args:
            client: An instance of AlmaApiClient.
        """
        self.client = client

    def get_bib(
            self,
            mms_id: str,
            view: Optional[str] = None,
            expand: Optional[str] = None
    ) -> Bib:
        """
        Retrieves a Bibliographic record by its MMS ID.

        Corresponds to GET /bibs/{mms_id}.

        Args:
            mms_id: The MMS ID of the Bib record.
            view: Optional. The view of the record ('full' or 'brief'). Default is 'full'.
            expand: Optional. Use 'p_avail' for physical availability, 'e_avail' for electronic,
                    'd_avail' for digital, or 'requests' for active requests. Combine with commas.

        Returns:
            A Bib object representing the Alma record.

        Raises:
            NotFoundError: If the MMS ID is not found.
            AlmaApiError: For other API or processing errors.
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided.")

        endpoint = f"/bibs/{mms_id}"
        params: Dict[str, Any] = {}
        if view:
            params["view"] = view
        if expand:
            params["expand"] = expand

        # Prefer JSON response for model mapping
        headers = {"Accept": "application/json"}

        response: Optional[requests.Response] = None
        try:
            response = self.client._get(endpoint, params=params, headers=headers)
            response_data = response.json()  # Raises JSONDecodeError on failure
            bib = Bib.model_validate(response_data)  # Use Pydantic V2 validation method
            return bib
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response for MMS ID {mms_id}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate Bib response data for MMS ID {mms_id}: {e}", response=response,
                               url=response.url) from e
        # Specific HTTP errors like NotFoundError are raised by client._get -> client._handle_response_errors

    def create_bib(
            self,
            bib_record_data: Union[Bib, Dict[str, Any], str]
    ) -> Bib:
        """
        Creates a new Bibliographic record in Alma.

        Corresponds to POST /bibs.

        Note: Creating records often requires specific normalization and handling based
              on local cataloging rules, which is beyond the scope of this basic client.
              Passing raw MARCXML might be necessary for complex cases.

        Args:
            bib_record_data: The data for the new Bib record. Can be:
                             - A Bib Pydantic object.
                             - A dictionary conforming to the Bib JSON structure (will be validated).
                             - A string containing valid MARCXML.

        Returns:
            A Bib object representing the newly created Alma record.

        Raises:
            InvalidInputError: If the input data is invalid according to Alma.
            AlmaApiError: For other API or processing errors.
        """
        endpoint = "/bibs"
        headers = {"Accept": "application/json"}  # Expect Bib JSON response
        payload: Any
        content_type: Optional[str] = None

        if isinstance(bib_record_data, str):
            # Assume raw XML string
            payload = bib_record_data.encode()  # Send as bytes
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(bib_record_data, dict):
            # Validate dictionary input before sending
            try:
                bib_obj = Bib.model_validate(bib_record_data)
                # Dump using alias for field names, exclude unset fields? Check Alma requirements.
                payload = bib_obj.model_dump(mode='json', by_alias=True, exclude_unset=True)
                content_type = "application/json"
                headers["Content-Type"] = content_type
                request_kwargs = {"json": payload}
            except ValidationError as e:
                raise InvalidInputError(f"Input dictionary failed Bib model validation: {e}") from e
        elif isinstance(bib_record_data, Bib):
            # Dump using alias for field names, exclude unset fields? Check Alma requirements.
            payload = bib_record_data.model_dump(mode='json', by_alias=True, exclude_unset=True)
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("bib_record_data must be a Bib object, dictionary, or XML string.")

        response: Optional[requests.Response] = None
        try:
            response = self.client._post(endpoint, headers=headers, **request_kwargs)
            response_data = response.json()
            created_bib = Bib.model_validate(response_data)
            return created_bib
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError("Failed to decode JSON response after creating Bib", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after creating Bib: {e}", response=response,
                               url=response.url) from e
        # Other errors (400 InvalidInputError, etc.) handled by client

    def update_bib(
            self,
            mms_id: str,
            bib_record_data: Union[Bib, Dict[str, Any], str],
            stale_record_action: Optional[str] = None,
            override_warning: Optional[bool] = None
            # Add other relevant query parameters as needed
    ) -> Bib:
        """
        Updates an existing Bibliographic record in Alma.

        Corresponds to PUT /bibs/{mms_id}.

        Requires sending the *complete* Bib record representation for update.

        Args:
            mms_id: The MMS ID of the Bib record to update.
            bib_record_data: The *complete* updated data for the Bib record. Can be:
                             - A Bib Pydantic object (recommended).
                             - A dictionary conforming to the Bib JSON structure (will be validated).
                             - A string containing valid MARCXML.
            stale_record_action: Optional. Action for stale data: 'cancel' or 'report'. Requires ETag handling.
                                 (ETag handling not implemented in this basic client version).
            override_warning: Optional. Set to True to override specific warnings (e.g., HldHasReqWarning).

        Returns:
            A Bib object representing the updated Alma record.

        Raises:
            ValueError: If mms_id is not provided.
            NotFoundError: If the MMS ID is not found.
            InvalidInputError: If the input data is invalid according to Alma.
            AlmaApiError: For other API or processing errors (e.g., concurrency conflicts if using ETag/stale checks).
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided for update.")

        endpoint = f"/bibs/{mms_id}"
        headers = {"Accept": "application/json"}  # Expect Bib JSON response
        params: Dict[str, Any] = {}
        if stale_record_action:
            # Note: Proper use requires sending If-Match header with ETag from GET response
            warnings.warn("stale_record_action requires ETag handling (If-Match header) which is not implemented.",
                          UserWarning)
            params["stale_record_action"] = stale_record_action
        if override_warning is not None:
            params["override_warning"] = str(override_warning).lower()

        payload: Any
        content_type: Optional[str] = None

        if isinstance(bib_record_data, str):
            # Assume raw XML string
            payload = bib_record_data.encode()
            content_type = "application/xml"
            headers["Content-Type"] = content_type
            request_kwargs = {"data": payload}
        elif isinstance(bib_record_data, dict):
            try:
                # It's generally best practice to GET the bib first, modify the object, then PUT.
                # Validating here ensures basic structure before sending.
                bib_obj = Bib.model_validate(bib_record_data)
                # Dump using alias, exclude unset might remove fields needed for update? Be cautious.
                payload = bib_obj.model_dump(mode='json', by_alias=True)  # Send all fields for PUT
                content_type = "application/json"
                headers["Content-Type"] = content_type
                request_kwargs = {"json": payload}
            except ValidationError as e:
                raise InvalidInputError(f"Input dictionary failed Bib model validation before update: {e}") from e
        elif isinstance(bib_record_data, Bib):
            # Dump using alias. Send all fields for PUT.
            payload = bib_record_data.model_dump(mode='json', by_alias=True)
            content_type = "application/json"
            headers["Content-Type"] = content_type
            request_kwargs = {"json": payload}
        else:
            raise TypeError("bib_record_data must be a Bib object, dictionary, or XML string.")

        response: Optional[requests.Response] = None
        try:
            response = self.client._put(endpoint, headers=headers, params=params, **request_kwargs)
            response_data = response.json()
            updated_bib = Bib.model_validate(response_data)
            return updated_bib
        except requests.exceptions.JSONDecodeError as e:
            raise AlmaApiError(f"Failed to decode JSON response after updating Bib {mms_id}", response=response,
                               url=response.url) from e
        except ValidationError as e:
            raise AlmaApiError(f"Failed to validate response data after updating Bib {mms_id}: {e}", response=response,
                               url=response.url) from e
        # Other errors (404 NotFoundError, 400 InvalidInputError, etc.) handled by client

    def delete_bib(
            self,
            mms_id: str,
            override_warning: Optional[bool] = None,
            reason: Optional[str] = None
    ) -> None:
        """
        Deletes a Bibliographic record from Alma.

        Corresponds to DELETE /bibs/{mms_id}.

        Warning: This action is permanent and potentially destructive. Use with caution.

        Args:
            mms_id: The MMS ID of the Bib record to delete.
            override_warning: Optional. Set to True to override specific warnings.
            reason: Optional. Deletion reason code.

        Returns:
            None on successful deletion (HTTP 204).

        Raises:
            ValueError: If mms_id is not provided.
            NotFoundError: If the MMS ID is not found.
            AlmaApiError: For other API errors (e.g., permissions, record cannot be deleted).
        """
        if not mms_id:
            raise ValueError("MMS ID must be provided for deletion.")

        endpoint = f"/bibs/{mms_id}"
        params: Dict[str, Any] = {}
        if override_warning is not None:
            params["override_warning"] = str(override_warning).lower()
        if reason:
            params["reason"] = reason

        try:
            # _delete should handle the 204 No Content success case internally
            # or raise an error for non-2xx statuses via _handle_response_errors
            self.client._delete(endpoint, params=params)
            return  # Explicitly return None on success
        except AlmaApiError as e:
            # Re-raise specific errors or the general one caught by the client
            raise e
