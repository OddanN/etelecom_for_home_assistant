"""Button platform for the Etelecom integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACCOUNT_ID, CONF_LOGIN, CONF_USER_ID, DOMAIN
from .formatting import format_device_name, format_device_slug


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([EtelecomRefreshButton(entry, coordinator)])


class EtelecomRefreshButton(CoordinatorEntity, ButtonEntity):
    _attr_name = 'Refresh'
    _attr_icon = 'mdi:refresh'
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ButtonEntity.__init__(self)
        account_id = str(entry.data.get(CONF_ACCOUNT_ID) or coordinator.data.get(CONF_ACCOUNT_ID) or 'unknown')
        user_id = str(entry.data.get(CONF_USER_ID) or coordinator.data.get(CONF_USER_ID) or 'unknown')
        self._attr_unique_id = f"{entry.entry_id}_{account_id}_refresh"
        self._attr_suggested_object_id = (
            f"{format_device_slug(entry.data.get(CONF_LOGIN), fallback='etelecom')}_refresh"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"account_{user_id}_{account_id}")},
            manufacturer='Etelecom',
            model='Personal Account',
            name=format_device_name(entry.data.get(CONF_LOGIN), fallback='ETelecom'),
        )

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
