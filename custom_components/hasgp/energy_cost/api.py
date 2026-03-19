from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import logging
import re

from aiohttp import ClientError, ClientSession

from .const import API_URL, DEFAULT_SERIES_NAME

_LOGGER = logging.getLogger(__name__)


class ApiError(Exception):
    """Base API error."""


class ApiConnectionError(ApiError):
    """Raised when the upstream API cannot be reached."""


class ApiDataError(ApiError):
    """Raised when the upstream payload is malformed."""


@dataclass(slots=True)
class TariffResult:
    """Normalized tariff payload."""

    cents_per_kwh: float
    sgd_per_kwh_ex_gst: float
    source_month: str
    fallback_used: bool
    data_series: str


class ApiClient:
    """Client for the data.gov.sg electricity tariff dataset."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_fetch_tariff(
        self,
        *,
        series_name: str = DEFAULT_SERIES_NAME,
        now: datetime | None = None,
    ) -> TariffResult:
        """Fetch and normalize the tariff for the current month with fallback."""
        now = now or datetime.now()

        try:
            async with self._session.get(API_URL) as response:
                response.raise_for_status()
                payload = await response.json()
        except (ClientError, TimeoutError) as err:
            raise ApiConnectionError(
                "Could not fetch tariff data"
            ) from err

        try:
            records = payload["result"]["records"]
        except (KeyError, TypeError) as err:
            raise ApiDataError("Unexpected API payload shape") from err

        row = self._find_series_row(records, series_name)
        current_key = now.strftime("%Y %b")
        previous_month = self._previous_month(now)
        previous_key = previous_month.strftime("%Y %b")

        resolved_current_key = self._resolve_month_key(row, current_key)
        resolved_previous_key = self._resolve_month_key(row, previous_key)

        raw_value = self._coerce_float(
            row.get(resolved_current_key) if resolved_current_key else None
        )
        fallback_used = False
        chosen_key = current_key

        if raw_value is None:
            raw_value = self._coerce_float(
                row.get(resolved_previous_key) if resolved_previous_key else None
            )
            fallback_used = True
            chosen_key = previous_key

        if raw_value is None:
            available_month_keys = sorted(
                key
                for key in row
                if self._looks_like_month_key(str(key))
            )
            raise ApiDataError(
                f"No tariff data found for {current_key} or {previous_key}. "
                f"Available month keys: {available_month_keys[-6:]}"
            )

        return TariffResult(
            cents_per_kwh=raw_value,
            sgd_per_kwh_ex_gst=raw_value / 100,
            source_month=chosen_key,
            fallback_used=fallback_used,
            data_series=self._series_value(row),
        )

    def _find_series_row(
        self, records: list[Mapping[str, object]], series_name: str
    ) -> Mapping[str, object]:
        for record in records:
            if self._series_value(record) == series_name:
                return record

        # Optional fallback to the current observed domestic row id if the field names
        # in the upstream response ever vary.
        for record in records:
            if str(record.get("id")) == "1":
                return record

        raise ApiDataError(
            f"Could not find tariff series row for {series_name}"
        )

    @staticmethod
    def _series_value(record: Mapping[str, object]) -> str:
        return str(
            record.get("DataSeries")
            or record.get("Data Series")
            or record.get("data_series")
            or ""
        )


    @classmethod
    def _resolve_month_key(
        cls, record: Mapping[str, object], wanted_key: str
    ) -> str | None:
        normalized_wanted = cls._normalize_key(wanted_key)

        for key in record:
            if cls._normalize_key(str(key)) == normalized_wanted:
                return str(key)

        return None

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    @classmethod
    def _looks_like_month_key(cls, value: str) -> bool:
        normalized = cls._normalize_key(value)
        return bool(re.fullmatch(r"_?\d{4}(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", normalized))

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value in (None, "", "na", "NA"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            _LOGGER.debug("Unable to convert tariff value %s to float", value)
            return None

    @staticmethod
    def _previous_month(value: datetime) -> datetime:
        if value.month == 1:
            return value.replace(year=value.year - 1, month=12)
        return value.replace(month=value.month - 1)
