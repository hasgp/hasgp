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
        """Fetch and normalize the latest available tariff."""
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
        available_months: list[tuple[datetime, str, float]] = []
        for key, value in row.items():
            month = self._parse_month_key(str(key))
            parsed_value = self._coerce_float(value)
            if (
                month is not None
                and parsed_value is not None
                and (month.year, month.month) <= (now.year, now.month)
            ):
                available_months.append((month, str(key), parsed_value))

        if not available_months:
            available_month_keys = sorted(
                key
                for key in row
                if self._looks_like_month_key(str(key))
            )
            raise ApiDataError(
                f"No tariff data found up to {current_key}. "
                f"Available month keys: {available_month_keys[-6:]}"
            )

        source_date, chosen_key, raw_value = max(
            available_months, key=lambda month: month[0]
        )
        fallback_used = (
            source_date.year != now.year or source_date.month != now.month
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


    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    @classmethod
    def _looks_like_month_key(cls, value: str) -> bool:
        normalized = cls._normalize_key(value)
        return bool(re.fullmatch(r"_?\d{4}(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", normalized))

    @classmethod
    def _parse_month_key(cls, value: str) -> datetime | None:
        normalized = cls._normalize_key(value)
        match = re.fullmatch(
            r"(\d{4})(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
            normalized,
        )
        if match is None:
            return None

        month_number = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }[match.group(2)]
        return datetime(int(match.group(1)), month_number, 1)

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value in (None, "", "na", "NA"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            _LOGGER.debug("Unable to convert tariff value %s to float", value)
            return None
