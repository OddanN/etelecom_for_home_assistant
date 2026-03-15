"""Version: 1.0.0. Options flow for the Etelecom integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
from .formatting import build_scan_interval_selector


class EtelecomOptionsFlow(OptionsFlow):
    """Handle options for Etelecom."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.build_options_schema(),
        )

    def build_options_schema(self) -> vol.Schema:
        """Build the options form schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
                    ),
                ): build_scan_interval_selector()
            }
        )
