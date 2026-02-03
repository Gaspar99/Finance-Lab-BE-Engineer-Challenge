from fastapi import Depends, Header, HTTPException

from app.config import get_api_key


def verify_api_key(x_api_key: str = Header(...)) -> None:
    """Check the X-API-Key header against the key stored in Secret Manager."""
    valid_key = get_api_key()
    if x_api_key != valid_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
