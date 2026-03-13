"""Version: 0.0.1. The Etelecom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .api import EtelecomApiClient, EtelecomAuthError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_LOGIN,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USER_ID,
    DOMAIN,
)
from .coordinator import EtelecomDataUpdateCoordinator

type EtelecomConfigEntry = ConfigEntry[EtelecomApiClient]

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the integration from YAML."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EtelecomConfigEntry) -> bool:
    """Set up Etelecom from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    client = EtelecomApiClient(
        hass=hass,
        login=entry.data[CONF_LOGIN],
        password=entry.data[CONF_PASSWORD],
        auth_data={
            key: entry.data[key]
            for key in (CONF_USER_ID, CONF_TOKEN)
            if entry.data.get(key) is not None
        }
        or None,
    )

    data_coordinator = EtelecomDataUpdateCoordinator(hass, client, entry)
    try:
        await data_coordinator.async_config_entry_first_refresh()
    except EtelecomAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except Exception as err:
        raise ConfigEntryNotReady(str(err)) from err

    latest_account_id = str(data_coordinator.data.get(CONF_ACCOUNT_ID, "unknown"))
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": data_coordinator,
        "account_id": latest_account_id,
    }
    entry.runtime_data = client

    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_USER_ID: client.user_id,
            CONF_TOKEN: client.token,
            CONF_ACCOUNT_ID: latest_account_id,
        },
    )

    _async_register_account_device(hass, entry, data_coordinator.data)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry after options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_account_device(
    hass: HomeAssistant,
    entry: ConfigEntry,
    payload: dict,
) -> None:
    """Register a single device for the configured account."""
    device_registry = dr.async_get(hass)
    account_id = str(payload.get(CONF_ACCOUNT_ID, "unknown"))
    user_id = entry.data.get(CONF_USER_ID) or payload.get(CONF_USER_ID) or "unknown"
    name = payload.get("name") or entry.title or "Etelecom"

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"account_{user_id}_{account_id}")},
        manufacturer="Etelecom",
        model="Personal Account",
        name=name,
    )
