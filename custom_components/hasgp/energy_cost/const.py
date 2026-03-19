from __future__ import annotations

CONF_ENTITY_NAMES = "entity_names"
CONF_ENERGY_ENTITY_IDS = "energy_entity_ids"

DEFAULT_GST_MULTIPLIER = 1.09
DEFAULT_SCAN_INTERVAL_HOURS = 24
DEFAULT_SERIES_NAME = "Low Tension Supplies - Domestic"

RESOURCE_ID = "d_61eac3cdb086814af485dcc682b75ae9"
API_URL = (
    "https://data.gov.sg/api/action/datastore_search"
    f"?resource_id={RESOURCE_ID}"
)

ATTR_SOURCE_MONTH = "source_month"
ATTR_FALLBACK_USED = "fallback_used"
ATTR_DATA_SERIES = "data_series"
ATTR_GST_RATE = "gst_rate"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"
ATTR_ENERGY_KWH = "energy_kwh"

TARIFF_KEY = "tariff"