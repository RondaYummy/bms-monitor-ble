import asyncio
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import python.db as db
from main import executor

auth_scheme = HTTPBearer()

_one_day = 24 * 60 * 60
TOKEN_LIFETIME_SECONDS = _one_day * 30

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    loop = asyncio.get_running_loop()

    is_valid = await loop.run_in_executor(
        executor, 
        db.is_token_valid_in_db, 
        token, 
        TOKEN_LIFETIME_SECONDS
    )
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return token