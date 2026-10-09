from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..const import DOMAIN
from .const import DEFAULT_GST_RATE, DEFAULT_TARIFF_SGD_PER_KWH, TARIFF_KEY

_LOGGER = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator[dict[str, object]]):
    """Provide the configured static electricity tariff."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

    async def _async_update_data(self) -> dict[str, object]:
        return {
            TARIFF_KEY: DEFAULT_TARIFF_SGD_PER_KWH,
            "tariff_source": "hardcoded",
            "gst_rate": DEFAULT_GST_RATE,
            "cents_per_kwh": DEFAULT_TARIFF_SGD_PER_KWH * 100,
        }
