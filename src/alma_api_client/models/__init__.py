"""
Pydantic Models for Alma API Objects.

This package contains Pydantic models representing various data structures
returned by or sent to the Ex Libris Alma REST APIs that this client supports.
"""

from .bib import Bib, CodeDesc
from .holding import Holding, BibLinkData
from .item import Item, ItemData
from .analytics import AnalyticsReportResults, AnalyticsColumn, AnalyticsPath

__all__ = [
    # From analytics.py
    "AnalyticsReportResults",
    "AnalyticsColumn",
    "AnalyticsPath",

    # From bib.py
    "Bib",
    "CodeDesc",  # Useful helper model

    # From holding.py
    "Holding",
    "BibLinkData",  # Useful helper model

    # From item.py
    "Item",
    "ItemData",  # Potentially useful for constructing item payloads
]
