"""Version: 0.0.1. Sensor platform for the Etelecom integration."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACCOUNT_ID, CONF_USER_ID, DOMAIN
from .coordinator import EtelecomDataUpdateCoordinator

RUSSIAN_RUBLE = "RUB"


class EtelecomSensorDescription(SensorEntityDescription):
    """Description of an Etelecom sensor."""


SENSORS: tuple[EtelecomSensorDescription, ...] = (
    EtelecomSensorDescription(
        key=CONF_ACCOUNT_ID,
        translation_key="account_id",
        name="Account ID",
    ),
    EtelecomSensorDescription(
        key="homebonus.sum",
        translation_key="bonus_balance",
        name="Bonus Balance",
    ),
    EtelecomSensorDescription(
        key="name",
        translation_key="customer_name",
        name="Customer Name",
    ),
    EtelecomSensorDescription(
        key="balance",
        translation_key="cash_balance",
        name="Cash Balance",
        native_unit_of_measurement=RUSSIAN_RUBLE,
    ),
    EtelecomSensorDescription(
        key="address",
        translation_key="contract_address",
        name="Contract Address",
    ),
    EtelecomSensorDescription(
        key="next_pay_date",
        translation_key="next_charge_date",
        name="Next Charge Date",
        device_class=SensorDeviceClass.DATE,
    ),
    EtelecomSensorDescription(
        key="charge_sum",
        translation_key="next_charge_amount",
        name="Next Charge Amount",
        native_unit_of_measurement=RUSSIAN_RUBLE,
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
        description: EtelecomSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = description
        self._attr_name = description.name
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement

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
            name=coordinator.data.get("name") or entry.title or "Etelecom",
        )

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        value = _extract_value(self.coordinator.data, self.entity_description.key)
        if value is None:
            return None

        if self.entity_description.device_class == SensorDeviceClass.DATE:
            return date.fromisoformat(str(value))

        if self.entity_description.native_unit_of_measurement == RUSSIAN_RUBLE:
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.key != "homebonus.sum":
            return None
        homebonus = self.coordinator.data.get("homebonus")
        if not isinstance(homebonus, dict):
            return None
        return {"in_program": homebonus.get("inProgram")}


def _extract_value(payload: dict[str, Any], key: str) -> Any:
    """Extract a value from the API payload using dot notation."""
    value: Any = payload
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
