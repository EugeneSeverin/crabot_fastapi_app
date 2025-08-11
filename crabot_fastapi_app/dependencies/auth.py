# auth.py
import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)
AUTH_TOKEN = os.getenv("STOCK_TRANSFER_FASTAPI_API_KEY")

def require_bearer(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:

    if not AUTH_TOKEN:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Auth is not configured on server")

    if credentials is None or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized",
                            headers={"WWW-Authenticate": "Bearer"})

    incoming = (credentials.credentials or "").strip()
    expected = AUTH_TOKEN.strip()
    if not secrets.compare_digest(incoming, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized",
                            headers={"WWW-Authenticate": "Bearer"})

    return True
