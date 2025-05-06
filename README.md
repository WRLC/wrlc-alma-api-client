# Alma API Client for Python

Python library providing a convenient interface for the Ex Libris Alma REST APIs.

**Disclaimer:** This is not an official Ex Libris product.

## Features

Currently supports operations within the following Alma API areas:

* **Analytics:** Retrieve reports (`/analytics/reports`), list paths (`/analytics/paths`).
* **Bibliographic Records:** Get, Create, Update, Delete Bib records (`/bibs`).
* **Holdings:** Get specific holding, get all holdings for a Bib, Create, Update, Delete Holdings (`/bibs/{mms_id}/holdings`).
* **Items:** Get specific item, get all items for a Holding, Create, Update, Delete Items (`/bibs/{mms_id}/holdings/{holding_id}/items`).

Uses Pydantic models for data validation and representation.

## Requirements

Requires Python 3.8+ (due to dependencies like `importlib.metadata` and Pydantic v2 features).

Dependencies: `requests`, `pydantic`, `xmltodict`.

## Quick Start

```python
from wrlc_alma_api_client import AlmaApiClient
from wrlc_alma_api_client.exceptions import AlmaApiError, NotFoundError
import os

# --- Configuration ---
# Best practice: Use environment variables or a config management tool
# api_key = os.getenv("ALMA_API_KEY")
api_key = "YOUR_ALMA_API_KEY"  # Replace with your key
alma_region = "NA"  # Your Alma region: NA, EU, APAC, etc.

if not api_key:
    raise ValueError("Please provide an ALMA_API_KEY.")

# --- Initialize Client ---
client = AlmaApiClient(api_key=api_key, region=alma_region)

# --- Example Usage ---
try:
    # Get a Bib record
    mms_id_to_get = "991234567890123"  # Example MMS ID
    bib = client.bibs.get_bib(mms_id=mms_id_to_get)
    print(f"Fetched Bib Title: {bib.title}")
    print(f"MMS ID: {bib.mms_id}")

    # Get items for a holding
    holding_id_to_get_items = "229999999000541"  # Example Holding ID
    items = client.items.get_holding_items(mms_id=mms_id_to_get, holding_id=holding_id_to_get_items)
    print(f"\nFound {len(items)} item(s) for Holding {holding_id_to_get_items}:")
    for item in items:
        print(f"- Item PID: {item.item_data.pid}, Barcode: {item.item_data.barcode}")

    # Get an Analytics report
    # report_path = "/shared/Your Institution/Reports/Your Report" # Example Path
    # report = client.analytics.get_report(path=report_path, limit=10)
    # print(f"\nFetched report. Finished: {report.is_finished}")
    # for row in report.rows:
    #     print(row)

except NotFoundError as e:
    print(f"Resource not found: {e}")
except AlmaApiError as e:
    print(f"An Alma API error occurred: {e}")
    # Access details if needed: e.status_code, e.detail, e.response
```

## Authentication

Requires an Alma API Key configured with the necessary read/write permissions for the desired API operations. The key is passed during client initialization.

## Error Handling

The client raises specific exceptions derived from `AlmaApiError` for issues:

* `AuthenticationError`: 401/403 errors.
* `NotFoundError`: 404 errors.
* `InvalidInputError`: 400 errors (often invalid request data).
* `RateLimitError`: 429 errors.
* `AlmaApiError`: Base class for other 4xx/5xx errors or network/parsing issues.

Exceptions contain `status_code`, the original `requests.Response` object (`response`), the requested `url`, and potentially extracted error details (`detail`) where possible.

# Development

This project uses [Poetry](https://python-poetry.org/) for dependency management and packaging.

1. Clone the repository.
2. Install dependencies: `poetry install --with dev`
3. Run tests: `poetry run pytest`

##License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.