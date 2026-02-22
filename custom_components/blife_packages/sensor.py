"""Sensor platform for BLife Packages integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PACKAGES,
    CONF_DEVICE_ID,
    DOMAIN,
    SENSOR_PACKAGES_COUNT,
    SENSOR_LAST_PACKAGE_REF,
)
from .coordinator import BLifePackagesCoordinator, BLifePackagesData


@dataclass(frozen=True, kw_only=True)
class BLifePackagesSensorEntityDescription(SensorEntityDescription):
    """Describe BLife Packages sensor entity."""

    value_fn: Callable[[BLifePackagesData], Any]
    extra_state_attributes_fn: Callable[[BLifePackagesData], dict[str, Any]] | None = (
        None
    )


def get_sensor_descriptions(firstname: str) -> list[BLifePackagesSensorEntityDescription]:
    """Generate sensor descriptions with dynamic naming based on firstname."""

    def get_last_package_ref(data: BLifePackagesData) -> str | None:
        """Get the ref number of the most recent uncollected package."""
        uncollected = [
            p for p in data.packages
            if p.latest_action != "collected" and p.created_date is not None
        ]
        if not uncollected:
            return None
        # Sort by created_date descending (most recent first)
        uncollected.sort(key=lambda p: p.created_date or datetime.min, reverse=True)
        return uncollected[0].ref_number

    def get_last_package_attrs(data: BLifePackagesData) -> dict[str, Any]:
        """Get attributes for the last package sensor."""
        uncollected = [
            p for p in data.packages
            if p.latest_action != "collected" and p.created_date is not None
        ]
        if not uncollected:
            return {"last_package": None}
        uncollected.sort(key=lambda p: p.created_date or datetime.min, reverse=True)
        return {"last_package": uncollected[0].to_dict()}

    return [
        BLifePackagesSensorEntityDescription(
            key=SENSOR_PACKAGES_COUNT,
            translation_key="packages_ready_to_collect",
            name=f"{firstname} Packages Ready to Collect",
            icon="mdi:package-variant",
            native_unit_of_measurement="packages",
            value_fn=lambda data: data.packages_ready_to_collect,
            extra_state_attributes_fn=lambda data: {
                ATTR_PACKAGES: [
                    p.to_dict()
                    for p in data.packages
                    if p.latest_action != "collected" and p.created_date is not None
                ],
            },
        ),
        BLifePackagesSensorEntityDescription(
            key=SENSOR_LAST_PACKAGE_REF,
            translation_key="last_package_ref_number",
            name=f"{firstname} Last Package Ref",
            icon="mdi:package-variant",
            value_fn=get_last_package_ref,
            extra_state_attributes_fn=get_last_package_attrs,
        ),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BLife Packages sensors based on a config entry."""
    coordinator: BLifePackagesCoordinator = hass.data[DOMAIN][entry.entry_id]

    firstname = entry.data.get("firstname", "User")
    sensor_descriptions = get_sensor_descriptions(firstname)

    async_add_entities(
        BLifePackagesSensor(
            coordinator=coordinator,
            description=description,
            entry=entry,
        )
        for description in sensor_descriptions
    )


class BLifePackagesSensor(
    CoordinatorEntity[BLifePackagesCoordinator], SensorEntity
):
    """Representation of a BLife Packages sensor."""

    entity_description: BLifePackagesSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BLifePackagesCoordinator,
        description: BLifePackagesSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_{description.key}"
        
        # Create device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
            name=f"BLife Concierge ({entry.data.get('firstname', 'User')})",
            manufacturer="BLife",
            model="Concierge Packages",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.extra_state_attributes_fn is None:
            return None
        return self.entity_description.extra_state_attributes_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

