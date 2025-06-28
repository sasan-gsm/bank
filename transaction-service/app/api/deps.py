# app/api/deps.py

import logging
from typing import List, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import security
from app.core.config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.auth_service_url}/api/v1/auth/login", scheme_name="JWT"
)


async def get_current_token(token: str = Depends(oauth2_scheme)) -> Dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.verify_token(token)
        if payload.get("type") != "access" or "sub" not in payload:
            raise credentials_exception
        return payload
    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        raise credentials_exception


async def get_current_user(payload: Dict = Depends(get_current_token)) -> Dict:
    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("sub"),
        "username": payload.get("username"),
        "is_superuser": payload.get("is_superuser", False),
        "permissions": payload.get("permissions", []),
        "roles": payload.get("roles", []),
    }


def require_permissions(required: List[str]):
    async def permission_checker(user: Dict = Depends(get_current_user)):
        if user.get("is_superuser"):
            return user
        missing = [perm for perm in required if perm not in user.get("permissions", [])]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return user

    return Depends(permission_checker)


# Reusable permission checkers
require_view_transactions = require_permissions(["can_view_transactions"])
require_create_transactions = require_permissions(["can_create_transactions"])
require_edit_transactions = require_permissions(["can_edit_transactions"])
require_verify_transactions = require_permissions(["can_verify_transactions"])
require_void_transactions = require_permissions(["can_void_transactions"])
require_view_bank_balances = require_permissions(["can_view_bank_balances"])
require_manage_bank_accounts = require_permissions(["can_manage_bank_accounts"])
