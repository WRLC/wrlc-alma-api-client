"""Holding model for Alma API client."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import warnings
from .utils import parse_boolean_optional, parse_datetime_optional


try:
    from .bib import CodeDesc
except ImportError:
    warnings.warn("Could not import CodeDesc from .bib, defining locally.", ImportWarning)


    class CodeDesc(BaseModel):
        """A common Alma pattern for representing a code and its description."""
        value: Optional[str] = Field(None, description="The code value.")
        desc: Optional[str] = Field(None, description="The description associated with the code.")


class BibLinkData(BaseModel):
    """Represents brief, linked Bibliographic data often included with Holding records."""
    mms_id: Optional[str] = Field(None, description="MMS ID of the linked Bib record.")
    title: Optional[str] = Field(None, description="Title of the linked Bib record.")
    author: Optional[str] = Field(None, description="Author of the linked Bib record.")
    isbn: Optional[str] = Field(None, description="ISBN of the linked Bib record.")
    issn: Optional[str] = Field(None, description="ISSN of the linked Bib record.")
    network_number: Optional[List[str]] = Field(
        default_factory=list, description="Network numbers of the linked Bib record."
    )
    place_of_publication: Optional[str] = Field(None, description="Place of publication of the linked Bib record.")
    date_of_publication: Optional[str] = Field(None, description="Date of publication of the linked Bib record.")
    publisher_const: Optional[str] = Field(None, description="Publisher of the linked Bib record.")
    link: Optional[str] = Field(None, description="Link to the full Bib record resource.")

    model_config = {
        "populate_by_name": True
    }


class Holding(BaseModel):
    """
    Represents an Alma Holding Record. (Using Pydantic V2 Validators)

    Based on the structure typically returned by the /almaws/v1/bibs/{mms_id}/holdings/{holding_id} endpoint.
    """
    holding_id: str = Field(..., description="The unique ID of the Holding record.")
    link: Optional[str] = Field(None, description="Permanent link (URL) to this Holding record resource.")

    created_by: Optional[str] = Field(None, description="User or process that created the record.")
    created_date: Optional[datetime] = Field(None, description="Date the record was created in Alma.")
    last_modified_by: Optional[str] = Field(None, description="User or process that last modified the record.")
    last_modified_date: Optional[datetime] = Field(None, description="Date the record was last modified.")

    suppress_from_publishing: Optional[bool] = Field(
        None, description="Indicates if the holding is suppressed from discovery (e.g., Primo)."
    )
    calculated_suppress_from_publishing: Optional[bool] = Field(
        None, alias='calculatedSuppressFromPublishing',
        description="Calculated suppression status considering related records."
    )

    originating_system: Optional[str] = Field(None, description="The originating system of the record.")
    originating_system_id: Optional[str] = Field(None, description="The ID within the originating system.")

    library: Optional[CodeDesc] = Field(None, description="The library code and description.")
    location: Optional[CodeDesc] = Field(None, description="The location code and description.")

    call_number_type: Optional[CodeDesc] = Field(None, description="The call number type code and description.")
    call_number: Optional[str] = Field(None, description="The call number string.")
    accession_number: Optional[str] = Field(None, description="Accession number, if applicable.")
    copy_id: Optional[str] = Field(None, description="Copy ID, if applicable (often used for bound units).")

    record_data: Optional[Dict[str, Any]] = Field(
        None,
        alias='anies',
        description="The core holding data, typically parsed from MARCXML or MARC JSON."
    )

    bib_data: Optional[BibLinkData] = Field(None, description="Brief data about the linked Bibliographic record.")

    # noinspection PyMethodParameters
    @field_validator('created_date', 'last_modified_date', mode='before')
    def _validate_datetime_str(cls, v: Any) -> Optional[datetime]:
        """Parse datetime strings before Pydantic validation."""
        return parse_datetime_optional(v)

    # noinspection PyMethodParameters
    @field_validator('suppress_from_publishing', 'calculated_suppress_from_publishing', mode='before')
    def _validate_boolean_str(cls, v: Any) -> Optional[bool]:
        """Parse boolean strings ('true'/'false') before Pydantic validation."""
        return parse_boolean_optional(v)

    model_config = {
        "populate_by_name": True
    }
