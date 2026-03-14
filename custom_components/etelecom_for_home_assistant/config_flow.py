"""Version: 0.0.1. Config flow for the Etelecom integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import EtelecomApiClient, EtelecomAuthError, EtelecomConnectionError, EtelecomError
from .const import CONF_ACCOUNT_ID, CONF_LOGIN, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_TOKEN, CONF_USER_ID, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN
from .options_flow import EtelecomOptionsFlow


# noinspection PyTypeChecker
class EtelecomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Etelecom."""

    VERSION = 1

    def __init__(self) -> None:
        self._entry_data: dict[str, str] | None = None
        self._title: str | None = None

    def is_matching(self, _other_flow: ConfigFlow) -> bool:
        return False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            login = user_input[CONF_LOGIN].strip()
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(login.lower())
            self._abort_if_unique_id_configured()

            client = EtelecomApiClient(hass=self.hass, login=login, password=password)
            try:
                data = await client.async_get_user_data()
            except EtelecomAuthError:
                errors['base'] = 'invalid_auth'
            except EtelecomConnectionError:
                errors['base'] = 'cannot_connect'
            except EtelecomError:
                errors['base'] = 'unknown'
            else:
                account_id = str(data.get(CONF_ACCOUNT_ID, ''))
                self._title = data.get('name') or f"Etelecom {login}"
                self._entry_data = {
                    CONF_LOGIN: login,
                    CONF_PASSWORD: password,
                    CONF_USER_ID: client.user_id,
                    CONF_TOKEN: client.token,
                    CONF_ACCOUNT_ID: account_id,
                }
                return await self.async_step_settings()

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required(CONF_LOGIN): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._entry_data is None:
            return self.async_abort(reason='unknown')

        if user_input is not None:
            return self.async_create_entry(
                title=self._title or self._entry_data[CONF_LOGIN],
                data=self._entry_data,
                options={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])},
            )

        return self.async_show_form(
            step_id='settings',
            data_schema=vol.Schema({
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=DEFAULT_SCAN_INTERVAL_HOURS,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=24,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement='h',
                    )
                )
            }),
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> EtelecomOptionsFlow:
        return EtelecomOptionsFlow(config_entry)
