"""Authentication dependencies for FastAPI-Users."""

from fastapi_users import FastAPIUsers

from app.domain.models import User
from app.auth.manager import get_user_manager
from app.auth.backend import auth_backend


# FastAPI-Users instance
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Dependencies
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
current_user_optional = fastapi_users.current_user(optional=True)
