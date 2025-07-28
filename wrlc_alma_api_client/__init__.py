"""Alma API Client Package"""

import importlib.metadata
import warnings

# --- Your other core imports ---
from .client import AlmaApiClient
# from .exceptions import AlmaApiError, AuthenticationError # Expose key exceptions

# --- Version Handling ---
try:
    # This retrieves the version metadata for the installed package.
    # The package name argument MUST match the distribution name
    # specified in your pyproject.toml (e.g., under [tool.poetry.name]
    # or [project.name]). It often uses hyphens.
    __version__ = importlib.metadata.version("wrlc-alma-api-client")

except importlib.metadata.PackageNotFoundError:
    # This happens if the package is not installed (e.g., you are running
    # the code directly from the source directory without installing it,
    # even in editable mode). It's good practice to handle this gracefully.
    __version__ = "0.0.0"  # Or "unknown", or any placeholder you prefer
    warnings.warn(
        "Could not determine package version using importlib.metadata. "
        "This is likely because the package is not installed. "
        f"Defaulting to {__version__}.",
        UserWarning
    )

# --- Expose public API ---
# Use __all__ to define what 'from alma_api_client import *' should import
# It's also good practice for defining the public interface.
__all__ = [
    'AlmaApiClient',
    # 'AlmaApiError',
    # 'AuthenticationError',
    # '__version__',
]

# Optional: Clean up the namespace if you don't want importlib or warnings
# accessible directly via the package.
# del importlib
# del warnings
