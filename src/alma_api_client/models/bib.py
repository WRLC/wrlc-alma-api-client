"""Bib model for Alma API client."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from .utils import parse_boolean_optional, parse_datetime_optional


class CodeDesc(BaseModel):
    """A common Alma pattern for representing a code and its description."""
    value: Optional[str] = Field(None, description="The code value.")
    desc: Optional[str] = Field(None, description="The description associated with the code.")


class Bib(BaseModel):
    """
    Represents an Alma Bibliographic Record. (Using Pydantic V2 Validators correctly)

    Based on the structure typically returned by the /almaws/v1/bibs/{mms_id} endpoint.
    Includes metadata, system information, and the core record data (often MARC).
    """
    mms_id: str = Field(..., description="The unique MMS ID of the bibliographic record.")
    title: Optional[str] = Field(None, description="The title of the record, often extracted from MARC.")
    author: Optional[str] = Field(None, description="The main author, often extracted from MARC.")
    isbn: Optional[str] = Field(None, description="ISBN identifier, often extracted from MARC.")
    issn: Optional[str] = Field(None, description="ISSN identifier, often extracted from MARC.")
    network_number: Optional[List[str]] = Field(
        default_factory=list,
        description="Network numbers associated with the record (e.g., OCLC number)."
    )
    place_of_publication: Optional[str] = Field(None, description="Place of publication.")
    date_of_publication: Optional[str] = Field(None, description="Date of publication (as string).")
    publisher_const: Optional[str] = Field(None, description="Publisher name.")

    link: Optional[str] = Field(None, description="Permanent link (URL) to this Bib record resource.")

    suppress_from_publishing: Optional[bool] = Field(
        None, description="Indicates if the record is suppressed from publishing (e.g., Primo)."
    )
    suppress_from_external_search: Optional[bool] = Field(
        None, description="Indicates if the record is suppressed from external search."
    )

    sync_with_oclc: Optional[str] = Field(None, description="OCLC synchronization status.")
    sync_with_libraries_australia: Optional[str] = Field(None,
                                                         description="Libraries Australia synchronization status.")

    originating_system: Optional[str] = Field(None, description="The originating system of the record.")
    originating_system_id: Optional[str] = Field(None, description="The ID within the originating system.")

    cataloging_level: Optional[CodeDesc] = Field(None, description="The cataloging level code and description.")
    brief_level: Optional[CodeDesc] = Field(None, description="The brief level code and description.")

    record_format: Optional[str] = Field(
        None, description="The format of the bibliographic record (e.g., 'marc21', 'unimarc')."
    )

    record_data: Optional[Dict[str, Any]] = Field(
        None,
        alias='record',
        description="The core bibliographic data, typically parsed from MARCXML or MARC JSON."
    )

    creation_date: Optional[datetime] = Field(None, description="Date the record was created in Alma.")
    created_by: Optional[str] = Field(None, description="User or process that created the record.")
    last_modified_date: Optional[datetime] = Field(None, description="Date the record was last modified.")
    last_modified_by: Optional[str] = Field(None, description="User or process that last modified the record.")

    # noinspection PyMethodParameters
    @field_validator('creation_date', 'last_modified_date', mode='before')
    def _validate_datetime_str(cls, v: Any) -> Optional[datetime]:
        """Parse datetime strings before Pydantic validation."""
        return parse_datetime_optional(v)

    # noinspection PyMethodParameters
    @field_validator('suppress_from_publishing', 'suppress_from_external_search', mode='before')
    def _validate_boolean_str(cls, v: Any) -> Optional[bool]:
        """Parse boolean strings ('true'/'false') before Pydantic validation."""
        return parse_boolean_optional(v)

    model_config = {
        "populate_by_name": True
    }
