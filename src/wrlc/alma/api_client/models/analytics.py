"""Analytics API Models"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
import warnings


class AnalyticsColumn(BaseModel):
    """
    Represents the metadata for a single column in an Analytics report result.
    """
    name: str = Field(
        description="The user-friendly name (heading) of the column.",
    )
    data_type: Optional[str] = Field(
        None,
        description="The data type of the column (e.g., 'string', 'integer', 'date').",
    )

    model_config = {
        "populate_by_name": True
    }


class AnalyticsReportResults(BaseModel):
    """
    Represents the results of an executed Alma Analytics report.
    """
    columns: List[AnalyticsColumn] = Field(
        default_factory=list,
        description="Metadata defining the columns included in the report rows."
    )
    rows: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The actual data rows of the report. "
                    "Each item in the list is a dictionary representing a row, "
                    "with keys corresponding to column names/headings."
    )
    is_finished: bool = Field(
        ...,
        description="Flag indicating if all results have been fetched.",
        alias="IsFinished"
    )
    resumption_token: Optional[str] = Field(
        None,
        description="Token to use for fetching the next chunk of results if "
                    "'is_finished' is False.",
        alias="ResumptionToken"
    )
    query_path: Optional[str] = Field(
        None,
        description="The path of the Analytics report that was executed."
    )
    job_id: Optional[str] = Field(
        None,
        description="Identifier for the asynchronous analytics job, if applicable.",
    )

    @model_validator(mode='after')
    def check_token_if_incomplete(self) -> 'AnalyticsReportResults':
        """Emit warning if results are incomplete but no token is provided."""
        if not self.is_finished and not self.resumption_token:
            warnings.warn(
                f"Analytics results for path '{self.query_path or 'unknown'}' "
                "are incomplete (is_finished=False) but no resumption_token "
                "was provided.", UserWarning
            )
        return self

    model_config = {
        "populate_by_name": True
    }


class AnalyticsPath(BaseModel):
    """
    Represents an available Analytics report or folder path.
    """
    path: str = Field(description="The full path identifier for the report or folder.")
    name: Optional[str] = Field(None, description="The display name of the report or folder.")
    type: Optional[str] = Field(None, description="Type of the object (e.g., 'Report', 'Folder').")
    description: Optional[str] = Field(None, description="Description of the report or folder.")

    model_config = {
        "populate_by_name": True
    }
