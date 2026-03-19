from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MODULE, MODULE_DEVICE_ENERGY_COST
from .energy_cost.sensor import async_setup_entry as async_setup_energy_cost_sensors


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HASGP sensors."""
    module = entry.data.get(CONF_MODULE)

    if module == MODULE_DEVICE_ENERGY_COST:
        await async_setup_energy_cost_sensors(hass, entry, async_add_entities)