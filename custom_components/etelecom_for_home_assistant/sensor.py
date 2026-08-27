"""Version: 1.0.0. Sensor platform for the Etelecom integration."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACCOUNT_ID, CONF_LOGIN, DOMAIN
from .coordinator import EtelecomDataUpdateCoordinator
from .formatting import build_device_info, format_device_slug

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
TARIFF_CHANGE_PLANNED = "\u0417\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u043e"
TARIFF_CHANGE_NOT_PLANNED = (
    "\u041d\u0435 \u0437\u0430\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u043e"
)
MBPS_SUFFIX = "\u041c\u0431\u0438\u0442/\u0441"
PAYMENTS_URL = "https://my.etelecom.ru/"
BONUS_URL = "https://my.etelecom.ru/bonus"
CURRENCY_PRECISION = Decimal("0.01")


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
    SensorEntityDescription(
        key="tariff_change",
        translation_key="tariff_change",
        icon="mdi:swap-horizontal-bold",
    ),
    SensorEntityDescription(
        key="active_services",
        translation_key="active_services",
        icon="mdi:format-list-bulleted-square",
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

        self._attr_device_info = build_device_info(entry.data, coordinator.data)

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
            return EntityCategory.DIAGNOSTIC
        if self._description.key in {
            CONF_ACCOUNT_ID,
            "name",
            "address",
            "network_connect_info.local_ip",
            "network_connect_info.external_ip",
            "active_services",
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
        return _build_native_value(
            self._description,
            self.coordinator.data,
            self.coordinator.last_successful_update,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        return _build_extra_state_attributes(self._description.key, self.coordinator.data)


def _extract_value(payload: dict[str, Any], key: str) -> Any:
    """Extract a value from the API payload using dot notation."""
    if key == "network_connect_info.local_ip":
        return _find_ip_entry(payload.get("network_connect_info"), external=False)
    if key == "network_connect_info.external_ip":
        return _find_ip_entry(payload.get("network_connect_info"), external=True)
    if key in {"tariff_change", "active_services"}:
        return payload.get("tariff_data_response")

    value: Any = payload
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _build_native_value(
        description: SensorEntityDescription,
        payload: dict[str, Any],
        last_successful_update: datetime | None,
) -> Any:
    """Build the sensor native value from coordinator payload."""
    if description.key == "last_update":
        return last_successful_update

    value = _extract_value(payload, description.key)
    if value is None:
        return None

    if description.device_class == SensorDeviceClass.DATE:
        return date.fromisoformat(str(value))

    formatter = _NATIVE_VALUE_FORMATTERS.get(description.key)
    if formatter is not None:
        return formatter(value, payload)

    if description.native_unit_of_measurement == RUSSIAN_RUBLE:
        return _to_decimal(value)

    return value


def _build_extra_state_attributes(sensor_key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build sensor attributes from coordinator payload."""
    builder = _EXTRA_ATTRIBUTE_BUILDERS.get(sensor_key)
    if builder is None:
        return None
    return builder(payload)


def _build_bonus_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build bonus sensor attributes."""
    return _extract_bonus_attributes(
        payload.get("homebonus"),
        payload.get("homebonus_details"),
        payload.get("create_date"),
    )


def _build_balance_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build money balance sensor attributes."""
    payment_attributes = _extract_payment_history_attributes(payload.get("payment_history"))
    return payment_attributes or None


def _build_current_tariff_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build current tariff sensor attributes."""
    return _extract_current_tariff_attributes(payload, payload.get("tariff_data_response"))


def _build_next_charge_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build next charge sensor attributes."""
    next_pay_date = payload.get("next_pay_date")
    if next_pay_date in (None, ""):
        return None
    return {"next_charge_date": next_pay_date}


def _build_local_ip_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build local IP sensor attributes."""
    return _extract_ip_attributes(payload.get("network_connect_info"), external=False)


def _build_external_ip_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build external IP sensor attributes."""
    return _extract_ip_attributes(
        payload.get("network_connect_info"),
        external=True,
        tariff_payload=payload.get("tariff_data_response"),
    )


def _build_tariff_change_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build tariff change sensor attributes."""
    return _extract_tariff_change_attributes(payload.get("tariff_data_response"), payload)


def _build_active_services_attributes(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build active services sensor attributes."""
    return _extract_active_services_attributes(payload.get("tariff_data_response"))


def _to_decimal(value: Any) -> Decimal | None:
    """Convert a value to decimal for currency sensors."""
    try:
        return Decimal(str(value)).quantize(CURRENCY_PRECISION, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


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


def _extract_ip_attributes(
        value: Any,
        *,
        external: bool,
        tariff_payload: Any = None,
) -> dict[str, Any] | None:
    """Build IP sensor attributes from the API response."""
    ip_entry = _find_ip_entry(value, external=external)
    if ip_entry is None:
        return None
    attributes = dict(ip_entry)
    if external:
        external_ip_service = _find_external_ip_service(tariff_payload, ip=str(ip_entry.get("ip") or ""))
        if external_ip_service is not None:
            attributes["service_cost"] = external_ip_service.get("service_cost") or external_ip_service.get("cost")
    return attributes


def _extract_current_tariff_attributes(payload: dict[str, Any], tariff_payload: Any) -> dict[str, Any] | None:
    """Build attributes for the current tariff sensor."""
    attributes: dict[str, Any] = {}
    tariff_name = payload.get("tariff_name")
    if tariff_name is not None:
        attributes["name"] = tariff_name

    tariff_speed = payload.get("tariff_speed")
    if tariff_speed is not None:
        attributes["speed"] = tariff_speed

    if not isinstance(tariff_payload, dict):
        return attributes or None

    current_tariff = tariff_payload.get("tariff_data")
    if not isinstance(current_tariff, dict):
        return attributes or None

    if current_tariff.get("id") is not None:
        attributes["id"] = current_tariff.get("id")
    return attributes or None


def _format_tariff_change_state(value: Any, payload: dict[str, Any]) -> str:
    """Return whether a tariff change is planned."""
    if _get_tariff_change_map(value, payload):
        return TARIFF_CHANGE_PLANNED
    return TARIFF_CHANGE_NOT_PLANNED


def _extract_tariff_change_attributes(value: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Build tariff change attributes from tariff-data and current tariff payload."""
    change_map = _get_tariff_change_map(value, payload)
    if not change_map:
        return None
    return change_map


def _get_tariff_change_map(value: Any, payload: dict[str, Any]) -> dict[str, str]:
    """Build a map of changed tariff fields."""
    if not isinstance(value, dict):
        return {}

    current_tariff = value.get("tariff_data")
    next_tariff = value.get("next_tariff_data")
    if not isinstance(current_tariff, dict) or not isinstance(next_tariff, dict):
        return {}

    comparisons = {
        "id": (
            str(current_tariff.get("id") or ""),
            str(next_tariff.get("id") or ""),
        ),
        "name": (
            str(payload.get("tariff_name") or current_tariff.get("name") or ""),
            str(next_tariff.get("name") or ""),
        ),
        "speed": (
            str(payload.get("tariff_speed") or current_tariff.get("speed") or ""),
            str(next_tariff.get("speed") or ""),
        ),
    }

    changes: dict[str, str] = {}
    for field, (current_value, new_value) in comparisons.items():
        if current_value and new_value and current_value != new_value:
            changes[field] = f'текущий "{current_value}" будет "{new_value}"'
    return changes


def _count_active_services(value: Any) -> int:
    """Return the number of active services."""
    return len(_get_active_services(value))


def _extract_active_services_attributes(value: Any) -> dict[str, Any] | None:
    """Build attributes for the active services sensor."""
    services = _get_active_services(value)
    attributes: dict[str, Any] = {"count": len(services)}
    for index, service in enumerate(services, start=1):
        attributes[f"service_{index}"] = _format_service_summary(service)
    return attributes


def _get_active_services(value: Any) -> list[dict[str, Any]]:
    """Extract active services from tariff-data payload."""
    if not isinstance(value, dict) or not value.get("success"):
        return []
    services = value.get("services")
    if not isinstance(services, list):
        return []
    return [
        service
        for service in services
        if isinstance(service, dict)
           and str(service.get("status_mnemonic") or "") == "active"
           and str(service.get("is_deleted") or "0") != "1"
    ]


def _format_service_summary(service: dict[str, Any]) -> str:
    """Build a compact summary for a service attribute."""
    service_name = service.get("service_name") or service.get("class_name") or service.get("id") or "service"
    service_cost = service.get("service_cost") or service.get("cost")
    parts = [str(service_name)]
    if service_cost not in (None, ""):
        parts.append(f"{service_cost} {RUSSIAN_RUBLE}")
    return " | ".join(parts)


def _find_external_ip_service(value: Any, *, ip: str) -> dict[str, Any] | None:
    """Find the active external IP service in tariff-data payload."""
    for service in _get_active_services(value):
        params = service.get("params")
        if isinstance(params, dict) and str(params.get("whiteip") or "") == ip:
            return service
        if str(service.get("service_name") or "") == "Аренда внешнего IP-адреса":
            return service
    return None


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


_NATIVE_VALUE_FORMATTERS: dict[str, Any] = {
    "tariff_speed": lambda value, _payload: _format_tariff_speed(value),
    "abonement_current": lambda value, _payload: _format_abonement_state(value),
    "tariff_change": _format_tariff_change_state,
    "active_services": lambda value, _payload: _count_active_services(value),
    "network_connect_info.local_ip": lambda value, _payload: _extract_ip_value(value),
    "network_connect_info.external_ip": lambda value, _payload: _extract_ip_value(value),
}

_EXTRA_ATTRIBUTE_BUILDERS: dict[str, Any] = {
    "homebonus.sum": _build_bonus_attributes,
    "balance": _build_balance_attributes,
    "tariff_speed": _build_current_tariff_attributes,
    "abonement_current": lambda payload: _format_abonement_attributes(payload.get("abonement_current")),
    "charge_sum": _build_next_charge_attributes,
    "network_connect_info.local_ip": _build_local_ip_attributes,
    "network_connect_info.external_ip": _build_external_ip_attributes,
    "tariff_change": _build_tariff_change_attributes,
    "active_services": _build_active_services_attributes,
}
