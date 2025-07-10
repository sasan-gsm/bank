"""Inter-service communication module for outbound service calls."""

import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urljoin

from app.core.config import settings
from app.core.cache import cache_manager
from app.streams.events import DomainEvent
import logging

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for managing service endpoints and configurations."""

    def __init__(self):
        """Initialize service registry with default configurations."""
        self.services = {
            "account-service": {
                "base_url": settings.account_service_url,
                "timeout": 30,
                "retry_count": 3,
                "health_endpoint": "/health",
            },
            "transaction-service": {
                "base_url": settings.transaction_service_url,
                "timeout": 30,
                "retry_count": 3,
                "health_endpoint": "/health",
            },
            "notification-service": {
                "base_url": settings.notification_service_url,
                "timeout": 15,
                "retry_count": 2,
                "health_endpoint": "/health",
            },
            "analytics-service": {
                "base_url": settings.analytics_service_url,
                "timeout": 10,
                "retry_count": 2,
                "health_endpoint": "/health",
            },
            "document-service": {
                "base_url": settings.document_service_url,
                "timeout": 10,
                "retry_count": 2,
                "health_endpoint": "/health",
            },
        }

    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific service."""
        return self.services.get(service_name)

    def get_service_url(self, service_name: str, endpoint: str = "") -> Optional[str]:
        """Get full URL for a service endpoint."""
        config = self.get_service_config(service_name)
        if not config or not config.get("base_url"):
            return None

        return urljoin(config["base_url"], endpoint.lstrip("/"))


class InterServiceClient:
    """Client for making HTTP calls to other microservices."""

    def __init__(self):
        """Initialize inter-service client."""
        self.registry = ServiceRegistry()
        self.client_timeout = httpx.Timeout(30.0, connect=10.0)

    async def _make_request(
        self,
        method: str,
        service_name: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to a service with retry logic."""
        config = self.registry.get_service_config(service_name)
        if not config:
            logger.error(f"Service {service_name} not found in registry")
            return None

        url = self.registry.get_service_url(service_name, endpoint)
        if not url:
            logger.error(f"Could not construct URL for {service_name}{endpoint}")
            return None

        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "X-Service-Name": "auth-service",
            "X-Request-ID": f"auth-{datetime.utcnow().timestamp()}",
        }
        if headers:
            request_headers.update(headers)

        # Use service-specific timeout or default
        request_timeout = timeout or config.get("timeout", 30)
        retry_count = config.get("retry_count", 3)

        for attempt in range(retry_count + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(request_timeout)
                ) as client:
                    if method.upper() == "GET":
                        response = await client.get(
                            url, headers=request_headers, params=data
                        )
                    elif method.upper() == "POST":
                        response = await client.post(
                            url, headers=request_headers, json=data
                        )
                    elif method.upper() == "PUT":
                        response = await client.put(
                            url, headers=request_headers, json=data
                        )
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=request_headers)
                    else:
                        logger.error(f"Unsupported HTTP method: {method}")
                        return None

                    response.raise_for_status()

                    # Try to parse JSON response
                    try:
                        result = response.json()
                        logger.info(
                            f"Successful {method} request to {service_name}{endpoint}"
                        )
                        return result
                    except json.JSONDecodeError:
                        # Return empty dict for successful non-JSON responses
                        return {
                            "status": "success",
                            "status_code": response.status_code,
                        }

            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout on attempt {attempt + 1} for {service_name}{endpoint}"
                )
                if attempt == retry_count:
                    logger.error(
                        f"All retry attempts failed for {service_name}{endpoint} due to timeout"
                    )
                    return None

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error {e.response.status_code} on attempt {attempt + 1} for {service_name}{endpoint}"
                )
                if attempt == retry_count:
                    logger.error(
                        f"All retry attempts failed for {service_name}{endpoint} with status {e.response.status_code}"
                    )
                    return None

            except Exception as e:
                logger.warning(
                    f"Unexpected error on attempt {attempt + 1} for {service_name}{endpoint}: {str(e)}"
                )
                if attempt == retry_count:
                    logger.error(
                        f"All retry attempts failed for {service_name}{endpoint}: {str(e)}"
                    )
                    return None

        return None

    async def get(
        self, service_name: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make GET request to a service."""
        return await self._make_request("GET", service_name, endpoint, data=params)

    async def post(
        self, service_name: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make POST request to a service."""
        return await self._make_request("POST", service_name, endpoint, data=data)

    async def put(
        self, service_name: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make PUT request to a service."""
        return await self._make_request("PUT", service_name, endpoint, data=data)

    async def delete(
        self, service_name: str, endpoint: str
    ) -> Optional[Dict[str, Any]]:
        """Make DELETE request to a service."""
        return await self._make_request("DELETE", service_name, endpoint)

    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        # Check cache first
        cache_key = f"service_health:{service_name}"
        cached_status = await cache_manager.get_cache(cache_key)

        if cached_status is not None:
            return bool(cached_status)

        config = self.registry.get_service_config(service_name)
        if not config:
            return False

        health_endpoint = config.get("health_endpoint", "/health")

        try:
            result = await self._make_request(
                "GET", service_name, health_endpoint, timeout=5
            )
            is_healthy = result is not None

            # Cache health status for 30 seconds
            await cache_manager.set_cache(cache_key, is_healthy, ttl=30)

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {str(e)}")
            await cache_manager.set_cache(
                cache_key, False, ttl=10
            )  # Cache failure for shorter time
            return False

    async def get_all_service_health(self) -> Dict[str, bool]:
        """Get health status of all registered services."""
        health_status = {}

        for service_name in self.registry.services.keys():
            health_status[service_name] = await self.check_service_health(service_name)

        return health_status


class UserValidationService:
    """Service for validating user operations with other services."""

    def __init__(self):
        """Initialize user validation service."""
        self.client = InterServiceClient()

    async def validate_account_creation(
        self, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate user data with account service before creation."""
        try:
            result = await self.client.post(
                "account-service",
                "/api/v1/accounts/validate",
                data={
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "full_name": user_data.get("full_name"),
                },
            )

            if result:
                return {
                    "valid": result.get("valid", True),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                }

            # If service is unavailable, allow creation but log warning
            logger.warning(
                "Account service unavailable for validation, proceeding with creation"
            )
            return {
                "valid": True,
                "errors": [],
                "warnings": ["Account service validation skipped"],
            }

        except Exception as e:
            logger.error(f"Error validating account creation: {str(e)}")
            return {
                "valid": True,
                "errors": [],
                "warnings": ["Account validation failed, proceeding anyway"],
            }

    async def notify_user_created(self, user_data: Dict[str, Any]) -> bool:
        """Notify other services about user creation."""
        try:
            # Notify account service
            account_result = await self.client.post(
                "account-service",
                "/api/v1/accounts/user-created",
                data={
                    "user_id": user_data.get("id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "full_name": user_data.get("full_name"),
                },
            )

            # Notify notification service
            notification_result = await self.client.post(
                "notification-service",
                "/api/v1/notifications/user-created",
                data={
                    "user_id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "full_name": user_data.get("full_name"),
                },
            )

            return account_result is not None or notification_result is not None

        except Exception as e:
            logger.error(f"Error notifying services about user creation: {str(e)}")
            return False

    async def notify_user_updated(
        self, user_id: int, updated_data: Dict[str, Any]
    ) -> bool:
        """Notify other services about user updates."""
        try:
            # Notify account service
            result = await self.client.put(
                "account-service",
                f"/api/v1/accounts/users/{user_id}",
                data=updated_data,
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error notifying services about user update: {str(e)}")
            return False

    async def notify_user_deleted(self, user_id: int) -> bool:
        """Notify other services about user deletion."""
        try:
            # Notify account service
            account_result = await self.client.delete(
                "account-service", f"/api/v1/accounts/users/{user_id}"
            )

            # Notify audit service
            audit_result = await self.client.post(
                "audit-service",
                "/api/v1/audit/user-deleted",
                data={"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
            )

            return account_result is not None or audit_result is not None

        except Exception as e:
            logger.error(f"Error notifying services about user deletion: {str(e)}")
            return False


# Global instances
inter_service_client = InterServiceClient()
user_validation_service = UserValidationService()
