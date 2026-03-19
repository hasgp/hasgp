from __future__ import annotations

from homeassistant.components.sensor import SensorEntityDescription
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .. import HasgpRuntimeData
from .const import (
    ATTR_DATA_SERIES,
    ATTR_ENERGY_KWH,
    ATTR_FALLBACK_USED,
    ATTR_GST_RATE,
    ATTR_SOURCE_ENTITY_ID,
    ATTR_SOURCE_MONTH,
    CONF_ENTITY_NAMES,
    CONF_ENERGY_ENTITY_IDS,
    TARIFF_KEY,
)
from .coordinator import Coordinator


TARIFF_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=TARIFF_KEY,
        name="Electricity Tariff",
    ),
)


@callback
def _device_identifier(config_entry: ConfigEntry) -> tuple[str, str]:
    """Return the device identifier."""
    return ("hasgp", config_entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from the config entry."""
    runtime_data: HasgpRuntimeData = config_entry.runtime_data
    coordinator = runtime_data.coordinator
    if coordinator is None:
        return

    energy_entity_ids = list(
        config_entry.options.get(
            CONF_ENERGY_ENTITY_IDS,
            config_entry.data.get(CONF_ENERGY_ENTITY_IDS, []),
        )
    )

    entity_names: dict[str, str] = dict(
        config_entry.options.get(
            CONF_ENTITY_NAMES,
            config_entry.data.get(CONF_ENTITY_NAMES, {}),
        )
    )

    entities: list[SensorEntity] = []

    for description in TARIFF_ENTITY_DESCRIPTIONS:
        entities.append(
            TariffEntity(
                coordinator=coordinator,
                parent_entry=config_entry,
                device_name="Device Energy Cost",
                description=description,
            )
        )

    for source_entity_id in energy_entity_ids:
        custom_name = entity_names.get(source_entity_id)
        entities.append(
            DeviceCostEntity(
                coordinator=coordinator,
                parent_entry=config_entry,
                source_entity_id=source_entity_id,
                custom_name=custom_name,
            )
        )

    async_add_entities(entities)


class BaseEntity(CoordinatorEntity[Coordinator], SensorEntity):
    """Base entity for HASGP."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Coordinator,
        parent_entry: ConfigEntry,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._parent_entry = parent_entry
        self._attr_device_info = DeviceInfo(
            identifiers={_device_identifier(parent_entry)},
            name=device_name,
            manufacturer="HASGP",
            model="Device Energy Cost",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            ATTR_SOURCE_MONTH: data.get("source_month"),
            ATTR_FALLBACK_USED: data.get("fallback_used"),
            ATTR_DATA_SERIES: data.get("data_series"),
            ATTR_GST_RATE: data.get("gst_rate"),
        }


class TariffEntity(BaseEntity):
    """Tariff sensor."""

    _attr_native_unit_of_measurement = "SGD/kWh"
    _attr_icon = "mdi:transmission-tower"

    def __init__(
        self,
        coordinator: Coordinator,
        parent_entry: ConfigEntry,
        device_name: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, parent_entry, device_name)
        self.entity_description = description
        self._attr_translation_key = "tariff"
        self._attr_unique_id = f"{parent_entry.entry_id}_tariff"
        self._attr_name = description.name

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return round(float(value), 5)


class DeviceCostEntity(BaseEntity):
    """Derived cost sensor for a selected energy entity."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "SGD"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(
        self,
        coordinator: Coordinator,
        parent_entry: ConfigEntry,
        source_entity_id: str,
        custom_name: str | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            parent_entry,
            "Device Energy Cost",
        )
        self._source_entity_id = source_entity_id
        self._attr_unique_id = (
            f"{parent_entry.entry_id}_cost_{source_entity_id.replace('.', '_')}"
        )
        self._attr_name = custom_name or source_entity_id
        self._unsub_track_state: CALLBACK_TYPE | None = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks after entity is added."""
        await super().async_added_to_hass()

        @callback
        def _async_source_state_changed(event: Event) -> None:
            self.async_write_ha_state()

        self._unsub_track_state = async_track_state_change_event(
            self.hass,
            [self._source_entity_id],
            _async_source_state_changed,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        if self._unsub_track_state is not None:
            self._unsub_track_state()
            self._unsub_track_state = None
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.hass.states.get(self._source_entity_id) is not None
            and self.coordinator.data.get(TARIFF_KEY) is not None
        )

    @property
    def native_value(self) -> float | None:
        source_state = self.hass.states.get(self._source_entity_id)
        if source_state is None:
            return None

        try:
            energy_kwh = Decimal(source_state.state)
            tariff = Decimal(str(self.coordinator.data[TARIFF_KEY]))
        except (InvalidOperation, KeyError):
            return None

        return float((energy_kwh * tariff).quantize(Decimal("0.01")))

    @property
    def suggested_display_precision(self) -> int:
        return 2

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        source_state = self.hass.states.get(self._source_entity_id)
        attrs[ATTR_SOURCE_ENTITY_ID] = self._source_entity_id
        attrs[ATTR_ENERGY_KWH] = None if source_state is None else source_state.state
        return attrs