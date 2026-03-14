"""Number platform for the Etelecom integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ACCOUNT_ID, CONF_SCAN_INTERVAL, CONF_USER_ID, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([EtelecomScanIntervalNumber(hass, entry, coordinator)])


class EtelecomScanIntervalNumber(NumberEntity):
    _attr_name = 'Scan Interval'
    _attr_icon = 'mdi:timer-outline'
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
        account_id = str(entry.data.get(CONF_ACCOUNT_ID) or coordinator.data.get(CONF_ACCOUNT_ID) or 'unknown')
        user_id = str(entry.data.get(CONF_USER_ID) or coordinator.data.get(CONF_USER_ID) or 'unknown')
        self._attr_unique_id = f"{entry.entry_id}_{account_id}_scan_interval"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"account_{user_id}_{account_id}")},
            manufacturer='Etelecom',
            model='Personal Account',
            name=coordinator.data.get('name') or entry.title or 'Etelecom',
        )

    @property
    def native_value(self) -> int:
        return int(self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS))

    async def async_set_native_value(self, value: float) -> None:
        value_int = max(1, min(24, int(round(value))))
        self.hass.config_entries.async_update_entry(self._entry, options={**self._entry.options, CONF_SCAN_INTERVAL: value_int})
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        self.async_write_ha_state()
