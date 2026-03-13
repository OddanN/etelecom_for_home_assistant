"""Version: 0.0.1. Coordinator for the Etelecom integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import EtelecomApiClient, EtelecomAuthError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EtelecomDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Etelecom updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EtelecomApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        self.client = client
        self.entry = entry
        update_interval = timedelta(
            hours=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS)
        )
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=update_interval,
        )

    async def async_refresh_data(self) -> dict[str, Any]:
        """Refresh data and return the latest payload."""
        await self.async_request_refresh()
        return self.data

    def get_latest_data(self) -> dict[str, Any]:
        """Return the latest cached payload."""
        return self.data

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch account data."""
        try:
            return await self.client.async_get_user_data()
        except EtelecomAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
