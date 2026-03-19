from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN
from .api import (
    ApiClient,
    ApiConnectionError,
    ApiDataError,
)
from .const import (
    DEFAULT_GST_MULTIPLIER,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_SERIES_NAME,
    TARIFF_KEY,
)

_LOGGER = logging.getLogger(__name__)


class Coordinator(DataUpdateCoordinator[dict[str, object]]):
    """Coordinate tariff updates from data.gov.sg."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._gst_multiplier: float = DEFAULT_GST_MULTIPLIER
        self._series_name: str = DEFAULT_SERIES_NAME
        scan_interval_hours = DEFAULT_SCAN_INTERVAL_HOURS
        self._api = ApiClient(async_get_clientsession(hass))

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=scan_interval_hours),
        )

    async def _async_update_data(self) -> dict[str, object]:
        try:
            result = await self._api.async_fetch_tariff(series_name=self._series_name)
        except ApiConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except ApiDataError as err:
            raise UpdateFailed(f"Data error: {err}") from err

        return {
            TARIFF_KEY: round(result.sgd_per_kwh_ex_gst * self._gst_multiplier, 5),
            "source_month": result.source_month,
            "fallback_used": result.fallback_used,
            "data_series": result.data_series,
            "gst_rate": round(self._gst_multiplier - 1, 4),
            "cents_per_kwh": result.cents_per_kwh,
        }
