import asyncio
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import python.db as db
from concurrent.futures import ThreadPoolExecutor

auth_scheme = HTTPBearer()

global_executor: ThreadPoolExecutor | None = None

_one_day = 24 * 60 * 60
TOKEN_LIFETIME_SECONDS = _one_day * 30

def initialize_auth_dependencies(executor_instance: ThreadPoolExecutor):
    global global_executor
    global_executor = executor_instance
    print("Executor for token verification initialized.")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    loop = asyncio.get_running_loop()

    if global_executor is None:
        raise RuntimeError("Executor was not initialized. Call initialize_auth_dependencies in main.py.")

    is_valid = await loop.run_in_executor(
        global_executor, 
        db.is_token_valid_in_db, 
        token, 
        TOKEN_LIFETIME_SECONDS
    )
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return token