"""Version: 0.0.1. API client for Etelecom."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL, API_PATH, CONF_TOKEN, CONF_USER_ID

_LOGGER = logging.getLogger(__name__)
_SENSITIVE_KEYS = {"password", CONF_TOKEN}


class EtelecomError(Exception):
    """Base exception for the integration."""


class EtelecomAuthError(EtelecomError):
    """Raised when authentication fails."""


class EtelecomConnectionError(EtelecomError):
    """Raised when the API is unavailable."""


class EtelecomResponseError(EtelecomError):
    """Raised when the API returned an unexpected payload."""


class EtelecomApiClient:
    """Thin API client for Etelecom."""

    def __init__(
        self,
        hass: HomeAssistant,
        login: str,
        password: str,
        auth_data: dict[str, str] | None = None,
    ) -> None:
        """Initialize the client."""
        self._session = async_get_clientsession(hass)
        self._login = login
        self._password = password
        self._user_id = auth_data.get(CONF_USER_ID) if auth_data else None
        self._token = auth_data.get(CONF_TOKEN) if auth_data else None

    @property
    def user_id(self) -> str | None:
        """Return the current user identifier."""
        return self._user_id

    @property
    def token(self) -> str | None:
        """Return the current auth token."""
        return self._token

    async def async_authenticate(self) -> dict[str, Any]:
        """Authenticate against the Etelecom API."""
        payload = await self._async_post(
            query="login",
            payload={"login": self._login, "password": self._password},
            request_name="login",
        )

        token = payload.get(CONF_TOKEN)
        user_id = payload.get(CONF_USER_ID)
        if not token or user_id is None:
            raise EtelecomAuthError("Invalid credentials")

        self._token = str(token)
        self._user_id = str(user_id)
        return payload

    async def async_get_user_data(self) -> dict[str, Any]:
        """Fetch the account data for the authenticated user."""
        if not self._user_id or not self._token:
            await self.async_authenticate()

        try:
            payload = await self._async_post(
                query="get-user",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="get-user",
            )
        except EtelecomAuthError:
            await self.async_authenticate()
            payload = await self._async_post(
                query="get-user",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="get-user",
            )

        token = payload.get(CONF_TOKEN)
        user_id = payload.get(CONF_USER_ID)
        if token:
            self._token = str(token)
        if user_id is not None:
            self._user_id = str(user_id)
        if payload.get("account_id") is None:
            raise EtelecomResponseError("Account payload did not include account_id")
        return payload

    async def _async_post(
        self,
        *,
        query: str,
        payload: dict[str, Any],
        request_name: str,
    ) -> dict[str, Any]:
        """Perform a POST request with the minimum required headers."""
        url = f"{API_BASE_URL}{API_PATH}?{query}"
        headers = self._build_headers()
        _LOGGER.debug(
            "Etelecom request: method=POST url=%s headers=%s payload=%s",
            url,
            _mask_mapping(headers),
            _mask_mapping(payload),
        )

        try:
            async with self._session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EtelecomConnectionError("Unable to connect to Etelecom") from err

        _LOGGER.debug(
            "Etelecom response: method=POST url=%s status=%s body=%s",
            url,
            response.status,
            _mask_text(response_text),
        )

        try:
            data = await response.json(content_type=None)
        except ValueError as err:
            raise EtelecomError("Invalid JSON response from Etelecom") from err

        if response.status in (401, 403):
            raise EtelecomAuthError("Authentication failed")

        if response.status >= 400:
            raise EtelecomError(f"Unexpected API response: {response.status}")

        if not data.get("success"):
            _LOGGER.debug(
                "Etelecom %s request failed, payload=%s, response=%s",
                request_name,
                _mask_mapping(payload),
                _mask_mapping(data),
            )
            raise EtelecomAuthError(f"{request_name} failed")

        return data

    @staticmethod
    def _build_headers() -> dict[str, str]:
        """Build headers accepted by the billing API."""
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://my.etelecom.ru",
            "Referer": "https://my.etelecom.ru/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
        }


def _mask_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive values in logs."""
    masked: dict[str, Any] = {}
    for key, value in data.items():
        if key in _SENSITIVE_KEYS and value is not None:
            masked[key] = "***"
            continue
        if isinstance(value, dict):
            masked[key] = _mask_mapping(value)
            continue
        masked[key] = value
    return masked


def _mask_text(text: str) -> str:
    """Avoid leaking secrets in logged raw response bodies."""
    try:
        payload = json.loads(text)
    except ValueError:
        return text

    if isinstance(payload, dict):
        return json.dumps(_mask_mapping(payload), ensure_ascii=False)
    return text
