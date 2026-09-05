"""Cognee Services Configuration Wrapper.

Re-exposes the central CogneeSettings from `backend.config.cognee`.
"""

from backend.config.cognee import CogneeSettings

__all__ = ["CogneeSettings"]
