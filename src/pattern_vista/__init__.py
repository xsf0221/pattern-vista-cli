"""Pattern Vista CLI — agent-friendly access to pattern win-rates and MA200 deviation rankings."""

__version__ = "0.2.1"

from .client import PatternVistaClient, PatternVistaError

__all__ = ["PatternVistaClient", "PatternVistaError", "__version__"]
