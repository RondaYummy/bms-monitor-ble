from python.data_store import data_store
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import (
    HTTPException,
    Depends,
)

auth_scheme = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    if not await data_store.is_token_valid(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return token