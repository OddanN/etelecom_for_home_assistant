"""Formatting helpers for the Etelecom integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
from homeassistant.util import slugify

from .const import CONF_ACCOUNT_ID, CONF_LOGIN, CONF_USER_ID, DOMAIN


def format_account_title(payload: dict[str, Any], fallback: str = "Etelecom") -> str:
    """Build the account title from profile fields."""
    raw_name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    phone = str(payload.get("phone") or "").strip()

    short_name = _shorten_name(raw_name) or raw_name or fallback
    contacts = ", ".join(value for value in (email, phone) if value)
    if not contacts:
        return short_name
    return f"{short_name} [{contacts}]"


def format_device_name(login: str | None, fallback: str = "ETelecom") -> str:
    """Build the device name from the account login."""
    normalized_login = str(login or "").strip()
    if not normalized_login:
        return fallback
    return f"ETelecom: {normalized_login}"


def format_device_slug(login: str | None, fallback: str = "etelecom") -> str:
    """Build the slug used as the entity_id prefix."""
    normalized_login = str(login or "").strip()
    if not normalized_login:
        return fallback
    return slugify(f"etelecom_{normalized_login}", separator="_")


def build_device_info(entry_data: Mapping[str, Any], coordinator_data: Mapping[str, Any]) -> DeviceInfo:
    """Build common device info for integration entities."""
    account_id = str(entry_data.get(CONF_ACCOUNT_ID) or coordinator_data.get(CONF_ACCOUNT_ID) or "unknown")
    user_id = str(entry_data.get(CONF_USER_ID) or coordinator_data.get(CONF_USER_ID) or "unknown")
    return DeviceInfo(
        identifiers={(DOMAIN, f"account_{user_id}_{account_id}")},
        manufacturer="Etelecom",
        model="Personal Account",
        name=format_device_name(entry_data.get(CONF_LOGIN), fallback="ETelecom"),
    )


def build_scan_interval_selector() -> NumberSelector:
    """Build the shared scan interval selector for flows."""
    return NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=24,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="h",
        )
    )


def _shorten_name(name: str) -> str:
    """Convert a full name like 'Surname Name Patronymic' to 'Surname N.P.'."""
    parts = [part for part in name.split() if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]

    surname = parts[0]
    initials = "".join(f"{part[0]}." for part in parts[1:] if part)
    if not initials:
        return surname
    return f"{surname} {initials}"
