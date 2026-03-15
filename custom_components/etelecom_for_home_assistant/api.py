"""Version: 0.0.1. API client for Etelecom."""

from __future__ import annotations

import json
import logging
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL, API_PATH, CONF_TOKEN, CONF_USER_ID

_LOGGER = logging.getLogger(__name__)
_SENSITIVE_KEYS = {"password", CONF_TOKEN}
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


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
        payload["abonement_current"] = await self.async_get_current_abonement()
        payload["network_connect_info"] = await self.async_get_network_connect_info()
        payload["payment_history"] = await self.async_get_payment_history(payload.get("create_date"))
        payload["homebonus_details"] = await self.async_get_homebonus_details(payload.get("create_date"))
        return payload

    async def async_get_current_abonement(self) -> dict[str, Any]:
        """Fetch the current abonement data for the authenticated user."""
        if not self._user_id or not self._token:
            await self.async_authenticate()

        try:
            return await self._async_post(
                query="abonement/current",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="abonement/current",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        except EtelecomAuthError:
            await self.async_authenticate()
            return await self._async_post(
                query="abonement/current",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="abonement/current",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )

    async def async_get_network_connect_info(self) -> dict[str, Any]:
        """Fetch network connection info for the authenticated user."""
        if not self._user_id or not self._token:
            await self.async_authenticate()

        try:
            return await self._async_post(
                query="network-settings/connect_info",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="network-settings/connect_info",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        except EtelecomAuthError:
            await self.async_authenticate()
            return await self._async_post(
                query="network-settings/connect_info",
                payload={
                    CONF_USER_ID: self._user_id,
                    CONF_TOKEN: self._token,
                },
                request_name="network-settings/connect_info",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )

    async def async_get_payment_history(self, create_date: Any) -> dict[str, Any]:
        """Fetch payment history from the account creation date until now."""
        if not self._user_id or not self._token:
            await self.async_authenticate()

        date_from = _date_to_unix_timestamp(create_date)
        date_to = int(datetime.now(MOSCOW_TZ).timestamp())
        payload = {
            CONF_USER_ID: self._user_id,
            CONF_TOKEN: self._token,
            "date_from": date_from,
            "date_to": date_to,
        }

        try:
            result = await self._async_post(
                query="payment/history",
                payload=payload,
                request_name="payment/history",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        except EtelecomAuthError:
            await self.async_authenticate()
            payload[CONF_USER_ID] = self._user_id
            payload[CONF_TOKEN] = self._token
            result = await self._async_post(
                query="payment/history",
                payload=payload,
                request_name="payment/history",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        result["date_from"] = date_from
        result["date_to"] = date_to
        result["create_date"] = create_date
        return result

    async def async_get_homebonus_details(self, create_date: Any) -> dict[str, Any]:
        """Fetch bonus history from the account creation date until now."""
        if not self._user_id or not self._token:
            await self.async_authenticate()

        from_str = _date_to_iso_date(create_date)
        to_str = datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d")
        payload = {
            CONF_USER_ID: self._user_id,
            CONF_TOKEN: self._token,
            "from_str": from_str,
            "to_str": to_str,
        }

        try:
            result = await self._async_post(
                query="homebonus/details",
                payload=payload,
                request_name="homebonus/details",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        except EtelecomAuthError:
            await self.async_authenticate()
            payload[CONF_USER_ID] = self._user_id
            payload[CONF_TOKEN] = self._token
            result = await self._async_post(
                query="homebonus/details",
                payload=payload,
                request_name="homebonus/details",
                fail_on_unsuccessful=False,
                content_type="application/x-www-form-urlencoded",
            )
        result["from_str"] = from_str
        result["to_str"] = to_str
        result["create_date"] = create_date
        return result

    async def _async_post(
        self,
        *,
        query: str,
        payload: dict[str, Any],
        request_name: str,
            fail_on_unsuccessful: bool = True,
            content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Perform a POST request with the minimum required headers."""
        url = f"{API_BASE_URL}{API_PATH}?{query}"
        headers = self._build_headers(content_type)
        _LOGGER.debug(
            "Etelecom request: method=POST url=%s headers=%s payload=%s",
            url,
            _mask_mapping(headers),
            _mask_mapping(payload),
        )

        try:
            request_kwargs: dict[str, Any] = {"headers": headers}
            if content_type == "application/json":
                request_kwargs["json"] = payload
            else:
                request_kwargs["data"] = json.dumps(payload)

            async with self._session.post(url, **request_kwargs) as response:
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

        if fail_on_unsuccessful and not data.get("success"):
            _LOGGER.debug(
                "Etelecom %s request failed, payload=%s, response=%s",
                request_name,
                _mask_mapping(payload),
                _mask_mapping(data),
            )
            raise EtelecomAuthError(f"{request_name} failed")

        return data

    @staticmethod
    def _build_headers(content_type: str = "application/json") -> dict[str, str]:
        """Build headers accepted by the billing API."""
        return {
            "Accept": "*/*",
            "Content-Type": content_type,
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


def _date_to_unix_timestamp(value: Any) -> int:
    """Convert a YYYY-MM-DD date to a Moscow midnight unix timestamp."""
    try:
        parsed_date = datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return int(datetime.now(MOSCOW_TZ).timestamp())
    return int(datetime.combine(parsed_date, time.min, tzinfo=MOSCOW_TZ).timestamp())


def _date_to_iso_date(value: Any) -> str:
    """Normalize a date value to YYYY-MM-DD."""
    try:
        return datetime.fromisoformat(str(value)).date().isoformat()
    except (TypeError, ValueError):
        return datetime.now(MOSCOW_TZ).date().isoformat()
