"""Item model for Alma API Client."""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
import warnings
from .utils import parse_boolean_optional, parse_datetime_optional, parse_date_optional


try:
    from .bib import CodeDesc
except ImportError:
    warnings.warn("Could not import CodeDesc from .bib, defining locally.", ImportWarning)


    class CodeDesc(BaseModel):
        value: Optional[str] = Field(None)
        desc: Optional[str] = Field(None)

try:
    from .holding import BibLinkData
except ImportError:
    warnings.warn("Could not import BibLinkData from .holding, defining locally.", ImportWarning)


    class BibLinkData(BaseModel):
        mms_id: Optional[str] = Field(None)
        title: Optional[str] = Field(None)
        author: Optional[str] = Field(None)
        link: Optional[str] = Field(None)


# noinspection PyMethodParameters
class ItemData(BaseModel):
    """Represents the core data specific to a physical or electronic item."""
    pid: str = Field(..., description="The unique Process ID (PID) of the item.")
    barcode: Optional[str] = Field(None, description="The item's barcode.")

    creation_date: Optional[datetime] = Field(None, description="Date the item record was created.")
    modification_date: Optional[datetime] = Field(None, description="Date the item record was last modified.")
    arrival_date: Optional[date] = Field(None, description="Date the item arrived (physical).")
    inventory_date: Optional[date] = Field(None, description="Date the item was last inventoried.")

    base_status: Optional[CodeDesc] = Field(None, description="Base status (e.g., 'Item in place'). '1' or '0'.")
    physical_material_type: Optional[CodeDesc] = Field(None, description="Physical material type (e.g., 'BOOK').")
    policy: Optional[CodeDesc] = Field(None, description="Item policy applied.")
    provenance: Optional[CodeDesc] = Field(None, description="Item provenance code.")
    process_type: Optional[CodeDesc] = Field(
        None, description="Current process type if not in place (e.g., 'LOAN', 'MISSING', 'HOLD_SHELF')."
    )

    library: Optional[CodeDesc] = Field(None, description="Current library code and description.")
    location: Optional[CodeDesc] = Field(None, description="Current location code and description.")
    alt_call_number: Optional[str] = Field(None, description="Alternative call number, if any.")
    alt_call_number_type: Optional[CodeDesc] = Field(None, description="Alternative call number type.")

    description: Optional[str] = Field(None, description="Item description (e.g., 'copy 1').")
    enumeration_a: Optional[str] = Field(None, description="Enumeration level A (e.g., volume).")
    enumeration_b: Optional[str] = Field(None, description="Enumeration level B (e.g., issue).")
    chronology_i: Optional[str] = Field(None, description="Chronology level I (e.g., year).")
    chronology_j: Optional[str] = Field(None, description="Chronology level J (e.g., month/season).")

    pieces: Optional[str] = Field(None, description="Number of pieces comprising the item.")
    pages: Optional[str] = Field(None, description="Number of pages or physical extent.")
    public_note: Optional[str] = Field(None, description="Public note displayed in discovery.")
    fulfillment_note: Optional[str] = Field(None, description="Note used in fulfillment processes.")
    internal_note_1: Optional[str] = Field(None, description="Internal note 1.")
    internal_note_2: Optional[str] = Field(None, description="Internal note 2.")
    internal_note_3: Optional[str] = Field(None, description="Internal note 3.")
    statistics_note_1: Optional[str] = Field(None, description="Statistics note 1.")
    statistics_note_2: Optional[str] = Field(None, description="Statistics note 2.")
    statistics_note_3: Optional[str] = Field(None, description="Statistics note 3.")

    is_magnetic: Optional[bool] = Field(None, description="Magnetic status flag.")
    requested: Optional[bool] = Field(None, description="Indicates if there is an active request on the item.")
    edition: Optional[str] = Field(None, description="Edition information specific to the item.")
    imprint: Optional[str] = Field(None, description="Imprint information specific to the item.")
    language: Optional[str] = Field(None, description="Language code of the item.")

    @field_validator('creation_date', 'modification_date', mode='before')
    def _validate_item_datetime_str(cls, v: Any) -> Optional[datetime]:
        return parse_datetime_optional(v)

    @field_validator('arrival_date', 'inventory_date', mode='before')
    def _validate_item_date_str(cls, v: Any) -> Optional[date]:
        return parse_date_optional(v)

    @field_validator('is_magnetic', 'requested', mode='before')
    def _validate_item_boolean_str(cls, v: Any) -> Optional[bool]:
        return parse_boolean_optional(v)

    model_config = {
        "populate_by_name": True
    }


# noinspection PyMethodParameters
class HoldingLinkDataForItem(BaseModel):
    """Represents linked Holding data relevant in the context of an Item."""
    holding_id: str = Field(..., description="ID of the parent Holding record.")
    link: Optional[str] = Field(None, description="Link to the full Holding record resource.")
    call_number: Optional[str] = Field(None, description="Call number inherited from the holding.")
    permanent_library: Optional[CodeDesc] = Field(None, alias='library', description="Permanent library from holding.")
    permanent_location: Optional[CodeDesc] = Field(
        None, alias='location', description="Permanent location from holding."
    )

    in_temp_location: Optional[bool] = Field(
        None, description="Flag indicating if item is in a temporary location defined on the holding."
    )
    temp_library: Optional[CodeDesc] = Field(None, description="Temporary library defined on the holding.")
    temp_location: Optional[CodeDesc] = Field(None, description="Temporary location defined on the holding.")
    temp_call_number_type: Optional[CodeDesc] = Field(
        None, description="Temporary call number type defined on the holding."
    )
    temp_call_number: Optional[str] = Field(None, description="Temporary call number defined on the holding.")
    temp_policy: Optional[CodeDesc] = Field(None, description="Temporary item policy defined on the holding.")

    @field_validator('in_temp_location', mode='before')
    def _validate_holding_boolean_str(cls, v: Any) -> Optional[bool]:
        return parse_boolean_optional(v)

    model_config = {
        "populate_by_name": True
    }


class Item(BaseModel):
    """
    Represents a full Alma Item record, typically including nested
    item_data, holding_data, and bib_data. (Using Pydantic V2 Validators)
    """
    item_data: ItemData = Field(..., description="Core data specific to this item.")
    holding_data: HoldingLinkDataForItem = Field(..., description="Data related to the item's parent holding.")
    bib_data: BibLinkData = Field(..., description="Data related to the item's parent bibliographic record.")
    link: Optional[str] = Field(None, description="Link to this Item resource, if available at the top level.")

    model_config = {
        "populate_by_name": True
    }
