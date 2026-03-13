"""Version: 0.0.1. Config flow for the Etelecom integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult

from .api import EtelecomApiClient, EtelecomAuthError, EtelecomConnectionError, EtelecomError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)
from .options_flow import EtelecomOptionsFlow


# noinspection PyTypeChecker
class EtelecomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Etelecom."""

    VERSION = 1

    def is_matching(self, _other_flow: ConfigFlow) -> bool:
        """Return whether another flow matches this one."""
        return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(login.lower())
            self._abort_if_unique_id_configured()

            client = EtelecomApiClient(
                hass=self.hass,
                login=login,
                password=password,
            )

            try:
                data = await client.async_get_user_data()
            except EtelecomAuthError:
                errors["base"] = "invalid_auth"
            except EtelecomConnectionError:
                errors["base"] = "cannot_connect"
            except EtelecomError:
                errors["base"] = "unknown"
            else:
                account_id = str(data.get(CONF_ACCOUNT_ID, ""))
                title = data.get("name") or f"Etelecom {login}"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_LOGIN: login,
                        CONF_PASSWORD: password,
                        CONF_USER_ID: client.user_id,
                        CONF_TOKEN: client.token,
                        CONF_ACCOUNT_ID: account_id,
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_HOURS},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOGIN): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> EtelecomOptionsFlow:
        """Get the options flow for this handler."""
        return EtelecomOptionsFlow(config_entry)
