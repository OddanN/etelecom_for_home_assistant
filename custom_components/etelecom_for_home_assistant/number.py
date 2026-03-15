"""Number platform for the Etelecom integration."""

from __future__ import annotations

import asyncio
from typing import Protocol

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ACCOUNT_ID, CONF_LOGIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN
from .formatting import build_device_info, format_device_slug


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the scan interval number from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([EtelecomScanIntervalNumber(hass, entry, coordinator)])


class _SupportsDeprecatedNumberSetValue(Protocol):
    """Protocol for the deprecated sync NumberEntity API used by the mixin."""

    def set_native_value(self, value: float) -> None:
        """Set the native number value."""

    def forward_native_value(self, value: float) -> None:
        """Forward the deprecated sync API to the native setter."""


class _NumberSetValueMixin:
    """Provide the deprecated sync API expected by pylint for NumberEntity."""

    def set_value(self: _SupportsDeprecatedNumberSetValue, value: float) -> None:
        """Delegate deprecated sync value updates to set_native_value."""
        self.forward_native_value(value)

    def forward_native_value(self: _SupportsDeprecatedNumberSetValue, value: float) -> None:
        """Forward deprecated value updates to the native setter."""
        self.set_native_value(value)


class EtelecomScanIntervalNumber(_NumberSetValueMixin, NumberEntity):
    """Number entity that controls the integration scan interval."""

    _attr_translation_key = 'scan_interval'
    _attr_icon = 'mdi:timer-cog-outline'
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = 'h'

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
        self.hass = hass
        self._entry = entry
        account_id = str(entry.data.get(CONF_ACCOUNT_ID) or coordinator.data.get(CONF_ACCOUNT_ID) or "unknown")
        self._attr_unique_id = f"{entry.entry_id}_{account_id}_scan_interval"
        self._attr_suggested_object_id = (
            f"{format_device_slug(entry.data.get(CONF_LOGIN), fallback='etelecom')}_scan_interval"
        )
        self._attr_device_info = build_device_info(entry.data, coordinator.data)

    @property
    def native_value(self) -> int:
        """Return the configured scan interval."""
        return int(self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS))

    async def async_set_native_value(self, value: float) -> None:
        """Persist a new scan interval and reload the config entry."""
        await self._async_apply_value(value)

    def set_native_value(self, value: float) -> None:
        """Persist a new scan interval when Home Assistant calls the sync API."""
        future = asyncio.run_coroutine_threadsafe(self._async_apply_value(value), self.hass.loop)
        future.result()

    async def _async_apply_value(self, value: float) -> None:
        """Persist a new scan interval and reload the config entry."""
        value_int = max(1, min(24, int(round(value))))
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_SCAN_INTERVAL: value_int},
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        self.async_write_ha_state()
