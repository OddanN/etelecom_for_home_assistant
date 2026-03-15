"""Version: 0.0.1. Sensor platform for the Etelecom integration."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACCOUNT_ID, CONF_LOGIN, CONF_USER_ID, DOMAIN
from .coordinator import EtelecomDataUpdateCoordinator
from .formatting import format_device_name, format_device_slug

RUSSIAN_RUBLE = "\u20bd"
BONUS_UNIT = "\u0431."
NO_ACTIVE_ABONEMENTS = (
    "\u041d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 "
    "\u0430\u0431\u043e\u043d\u0435\u043c\u0435\u043d\u0442\u043e\u0432"
)
ACTIVE_UNTIL_PREFIX = (
    "\u0414\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442 \u0434\u043e"
)
ACTIVE_ABONEMENT_FALLBACK = "\u0414\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442"
MBPS_SUFFIX = "\u041c\u0431\u0438\u0442/\u0441"
PAYMENTS_URL = "https://my.etelecom.ru/"
BONUS_URL = "https://my.etelecom.ru/bonus"


SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=CONF_ACCOUNT_ID,
        translation_key="account_id",
        icon="mdi:card-account-details-outline",
    ),
    SensorEntityDescription(
        key="homebonus.sum",
        translation_key="bonus_balance",
        native_unit_of_measurement=BONUS_UNIT,
        icon="mdi:star-circle-outline",
    ),
    SensorEntityDescription(
        key="name",
        translation_key="customer_name",
        icon="mdi:account-circle-outline",
    ),
    SensorEntityDescription(
        key="balance",
        translation_key="cash_balance",
        native_unit_of_measurement=RUSSIAN_RUBLE,
        icon="mdi:wallet-outline",
    ),
    SensorEntityDescription(
        key="address",
        translation_key="contract_address",
        icon="mdi:home-map-marker",
    ),
    SensorEntityDescription(
        key="charge_sum",
        translation_key="next_charge",
        native_unit_of_measurement=RUSSIAN_RUBLE,
        icon="mdi:cash-sync",
    ),
    SensorEntityDescription(
        key="tariff_speed",
        translation_key="current_tariff",
        icon="mdi:speedometer",
    ),
    SensorEntityDescription(
        key="abonement_current",
        translation_key="abonement",
        icon="mdi:calendar-check-outline",
    ),
    SensorEntityDescription(
        key="network_connect_info.local_ip",
        translation_key="local_ip",
        icon="mdi:ip-network-outline",
    ),
    SensorEntityDescription(
        key="network_connect_info.external_ip",
        translation_key="external_ip",
        icon="mdi:wan",
    ),
    SensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-check-outline",
    ),
)


async def async_setup_entry(
    hass,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Etelecom sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        EtelecomSensor(coordinator, entry, description) for description in SENSORS
    )


class EtelecomSensor(CoordinatorEntity[EtelecomDataUpdateCoordinator], SensorEntity):
    """Representation of an Etelecom sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EtelecomDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_suggested_object_id = (
            f"{format_device_slug(entry.data.get(CONF_LOGIN), fallback='etelecom')}_"
            f"{description.translation_key or description.key.replace('.', '_')}"
        )
        if description.key == "last_update":
            self._attr_entity_registry_enabled_default = False

        account_id = str(
            entry.data.get(CONF_ACCOUNT_ID) or coordinator.data.get(CONF_ACCOUNT_ID) or "unknown"
        )
        user_id = str(
            entry.data.get(CONF_USER_ID) or coordinator.data.get(CONF_USER_ID) or "unknown"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"account_{user_id}_{account_id}")},
            manufacturer="Etelecom",
            model="Personal Account",
            name=format_device_name(entry.data.get(CONF_LOGIN), fallback="ETelecom"),
        )

    @property
    def translation_key(self) -> str | None:
        """Return the translation key for the entity."""
        return self._description.translation_key

    @property
    def device_class(self) -> SensorDeviceClass | str | None:
        """Return the device class of the sensor."""
        return self._description.device_class

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the entity category for the sensor."""
        if self._description.key == "last_update":
            return EntityCategory.CONFIG
        if self._description.key in {
            CONF_ACCOUNT_ID,
            "name",
            "address",
            "network_connect_info.local_ip",
            "network_connect_info.external_ip",
        }:
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit of measurement."""
        return self._description.native_unit_of_measurement

    @property
    def icon(self) -> str | None:
        """Return the entity icon."""
        return self._description.icon

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        if self._description.key == "last_update":
            return self.coordinator.last_successful_update

        value = _extract_value(self.coordinator.data, self._description.key)
        if value is None:
            return None

        if self._description.device_class == SensorDeviceClass.DATE:
            return date.fromisoformat(str(value))

        if self._description.key == "tariff_speed":
            return _format_tariff_speed(value)

        if self._description.key == "abonement_current":
            return _format_abonement_state(value)

        if self._description.key in {"network_connect_info.local_ip", "network_connect_info.external_ip"}:
            return _extract_ip_value(value)

        if self._description.native_unit_of_measurement == RUSSIAN_RUBLE:
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self._description.key == "homebonus.sum":
            return _extract_bonus_attributes(
                self.coordinator.data.get("homebonus"),
                self.coordinator.data.get("homebonus_details"),
                self.coordinator.data.get("create_date"),
            )

        if self._description.key == "balance":
            payment_attributes = _extract_payment_history_attributes(
                self.coordinator.data.get("payment_history"),
            )
            return payment_attributes or None

        if self._description.key == "tariff_speed":
            tariff_name = self.coordinator.data.get("tariff_name")
            return {"name": tariff_name} if tariff_name is not None else None

        if self._description.key == "abonement_current":
            return _format_abonement_attributes(self.coordinator.data.get("abonement_current"))

        if self._description.key == "charge_sum":
            next_pay_date = self.coordinator.data.get("next_pay_date")
            if next_pay_date in (None, ""):
                return None
            return {"next_charge_date": next_pay_date}

        if self._description.key == "network_connect_info.local_ip":
            return _extract_ip_attributes(self.coordinator.data.get("network_connect_info"), external=False)

        if self._description.key == "network_connect_info.external_ip":
            return _extract_ip_attributes(self.coordinator.data.get("network_connect_info"), external=True)

        return None


def _extract_value(payload: dict[str, Any], key: str) -> Any:
    """Extract a value from the API payload using dot notation."""
    if key == "network_connect_info.local_ip":
        return _find_ip_entry(payload.get("network_connect_info"), external=False)
    if key == "network_connect_info.external_ip":
        return _find_ip_entry(payload.get("network_connect_info"), external=True)

    value: Any = payload
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _format_tariff_speed(value: Any) -> str | None:
    """Convert tariff speed value to a readable string."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return f"{normalized} {MBPS_SUFFIX}"


def _format_abonement_state(value: Any) -> str:
    """Build the abonement sensor state."""
    if not isinstance(value, dict) or not value.get("success"):
        return NO_ACTIVE_ABONEMENTS

    abonements = value.get("abonements")
    if not isinstance(abonements, list) or not abonements:
        return NO_ACTIVE_ABONEMENTS

    current_abonement = abonements[0]
    expire_date = _format_unix_date(current_abonement.get("expire_date"))
    if expire_date is None:
        return ACTIVE_ABONEMENT_FALLBACK
    return f"{ACTIVE_UNTIL_PREFIX} {expire_date}"


def _format_abonement_attributes(value: Any) -> dict[str, Any] | None:
    """Build abonement sensor attributes from the API response."""
    if not isinstance(value, dict):
        return None

    attributes: dict[str, Any] = {"success": value.get("success")}
    abonements = value.get("abonements")
    if not isinstance(abonements, list) or not abonements:
        return attributes

    current_abonement = dict(abonements[0])
    current_abonement["start_date"] = _format_unix_date(current_abonement.get("start_date"))
    current_abonement["expire_date"] = _format_unix_date(current_abonement.get("expire_date"))
    attributes.update(current_abonement)
    attributes["abonements"] = abonements
    return attributes


def _format_unix_date(value: Any) -> str | None:
    """Convert a unix timestamp string to dd.mm.yyyy."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(str(value))
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y")


def _find_ip_entry(value: Any, *, external: bool) -> dict[str, Any] | None:
    """Find local or external IP entry in the network info payload."""
    if not isinstance(value, dict) or not value.get("success"):
        return None

    ips = value.get("ips")
    if not isinstance(ips, list):
        return None

    expected_flag = "1" if external else "0"
    for ip_entry in ips:
        if isinstance(ip_entry, dict) and str(ip_entry.get("ip_is_external")) == expected_flag:
            return ip_entry
    return None


def _extract_ip_value(value: Any) -> str | None:
    """Extract the IP address from the selected entry."""
    if not isinstance(value, dict):
        return None
    ip = value.get("ip")
    if ip in (None, ""):
        return None
    return str(ip)


def _extract_ip_attributes(value: Any, *, external: bool) -> dict[str, Any] | None:
    """Build IP sensor attributes from the API response."""
    ip_entry = _find_ip_entry(value, external=external)
    if ip_entry is None:
        return None
    return dict(ip_entry)


def _extract_payment_history_attributes(value: Any) -> dict[str, Any]:
    """Build attributes for the payment history sensor."""
    attributes: dict[str, Any] = {
        "payments_url": PAYMENTS_URL,
    }
    if not isinstance(value, dict):
        return attributes
    history = value.get("history")
    if not isinstance(history, list):
        attributes["count"] = 0
        return attributes

    formatted_history = [_format_payment_history_item(item) for item in history if isinstance(item, dict)]
    attributes["count"] = len(formatted_history)
    for index, item in enumerate(reversed(formatted_history[-10:]), start=1):
        attributes[f"operation_{index}"] = _format_payment_history_summary(item)
    return attributes


def _extract_bonus_attributes(
        homebonus: Any,
        details_payload: Any,
        create_date: Any,
) -> dict[str, Any] | None:
    """Build attributes for the bonus balance sensor."""
    attributes: dict[str, Any] = {
        "bonus_url": BONUS_URL,
        "create_date": create_date,
    }

    if isinstance(homebonus, dict):
        attributes["in_program"] = homebonus.get("inProgram")

    if not isinstance(details_payload, dict):
        return attributes

    attributes["success"] = details_payload.get("success")
    attributes["from_str"] = details_payload.get("from_str")
    attributes["to_str"] = details_payload.get("to_str")

    details = details_payload.get("details")
    if not isinstance(details, list):
        attributes["count"] = 0
        return attributes

    formatted_details = [
        _format_bonus_history_item(item) for item in details if isinstance(item, dict)
    ]
    attributes["count"] = len(formatted_details)
    for index, item in enumerate(formatted_details, start=1):
        attributes[f"operation_{index}"] = _format_bonus_history_summary(item)
    return attributes


def _format_payment_history_item(item: dict[str, Any]) -> dict[str, Any]:
    """Add a readable date to a payment history item."""
    formatted = dict(item)
    formatted["date_formatted"] = _format_unix_datetime(item.get("date"))
    return formatted


def _format_payment_history_summary(item: dict[str, Any]) -> str:
    """Build a compact one-line payment history entry for HA attributes."""
    date_formatted = item.get("date_formatted") or "unknown date"
    amount = item.get("summ")
    type_name = item.get("type") or item.get("method_name") or ""

    parts = [str(date_formatted)]
    if amount not in (None, ""):
        parts.append(f"{amount} {RUSSIAN_RUBLE}")
    if type_name:
        parts.append(str(type_name))
    return " | ".join(parts)


def _format_bonus_history_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a bonus history item for readable HA attributes."""
    formatted = dict(item)
    formatted.pop("expire_date", None)
    return formatted


def _format_bonus_history_summary(item: dict[str, Any]) -> str:
    """Build a compact one-line bonus history entry for HA attributes."""
    trans_date = item.get("trans_date") or "unknown date"
    bonus_value = item.get("bonus_value")
    description = item.get("description") or ""

    parts = [str(trans_date)]
    if bonus_value not in (None, ""):
        parts.append(f"{bonus_value} {BONUS_UNIT}")
    if description:
        parts.append(str(description))
    return " | ".join(parts)


def _format_unix_datetime(value: Any) -> str | None:
    """Convert a unix timestamp string to dd.mm.yyyy HH:MM:SS."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(str(value))
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")
