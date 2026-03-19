from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_MODULE, MODULE_DEVICE_ENERGY_COST
from .energy_cost.coordinator import Coordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class HasgpRuntimeData:
    coordinator: Coordinator | None = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    module = entry.data.get(CONF_MODULE)

    runtime_data = HasgpRuntimeData()

    if module == MODULE_DEVICE_ENERGY_COST:
        coordinator = Coordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        runtime_data.coordinator = coordinator

    entry.runtime_data = runtime_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)