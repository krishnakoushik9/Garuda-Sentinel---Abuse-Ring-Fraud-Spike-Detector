"""Cognee Cloud Configuration Settings.

Exposes CogneeSettings using the project's existing configuration system in `src/config.py`.
"""

from src.config import COGNEE_API_KEY, COGNEE_BASE_URL, COGNEE_TENANT_ID, COGNEE_USER_ID

class CogneeSettings:
    COGNEE_API_KEY = COGNEE_API_KEY
    COGNEE_BASE_URL = COGNEE_BASE_URL
    COGNEE_TENANT_ID = COGNEE_TENANT_ID
    COGNEE_USER_ID = COGNEE_USER_ID

    @classmethod
    def validate(cls) -> None:
        """Validates that all required Cognee environment variables are set.
        Raises ValueError if any required settings are missing.
        """
        missing = []
        if not cls.COGNEE_API_KEY:
            missing.append("COGNEE_API_KEY")
        if not cls.COGNEE_BASE_URL:
            missing.append("COGNEE_BASE_URL")
        if not cls.COGNEE_TENANT_ID:
            missing.append("COGNEE_TENANT_ID")
        if not cls.COGNEE_USER_ID:
            missing.append("COGNEE_USER_ID")
        
        if missing:
            raise ValueError(f"Missing required Cognee configuration variable(s): {', '.join(missing)}")
