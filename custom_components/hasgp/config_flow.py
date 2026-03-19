from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.core import callback

from .const import (
    CONF_MODULE,
    DOMAIN,
    MODULE_DEVICE_ENERGY_COST,
    MODULE_WEATHER,
)
from .energy_cost.const import CONF_ENERGY_ENTITY_IDS, CONF_ENTITY_NAMES

def _module_unique_id(module: str) -> str:
    """Return the unique ID for a singleton HASGP module."""
    return f"{DOMAIN}_{module}"

def _entity_name_key(index: int) -> str:
    return f"sensor_name_{index}"


def _friendly_name(hass, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state is None:
        return entity_id
    return state.attributes.get("friendly_name", entity_id)


def _build_entity_schema(
    defaults: Mapping[str, Any] | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_ENERGY_ENTITY_IDS,
                default=defaults.get(CONF_ENERGY_ENTITY_IDS, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.ENERGY,
                    multiple=True,
                    reorder=True,
                )
            ),
        }
    )


def _build_naming_schema(
    hass,
    entity_ids: list[str],
    existing_names: dict[str, str] | None = None,
) -> vol.Schema:
    existing_names = existing_names or {}
    schema: dict[Any, Any] = {}

    for i, entity_id in enumerate(entity_ids):
        schema[
            vol.Optional(
                _entity_name_key(i),
                default=existing_names.get(entity_id, _friendly_name(hass, entity_id)),
            )
        ] = selector.TextSelector()

    return vol.Schema(schema)


class HASGPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._selected_entity_ids: list[str] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return HASGPOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=[
                MODULE_DEVICE_ENERGY_COST,
                MODULE_WEATHER,
            ],
        )

    async def async_step_device_energy_cost(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure the Device Energy Cost module."""
        await self.async_set_unique_id(_module_unique_id(MODULE_DEVICE_ENERGY_COST))
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._selected_entity_ids = list(user_input[CONF_ENERGY_ENTITY_IDS])
            return await self.async_step_device_energy_cost_naming()

        return self.async_show_form(
            step_id="device_energy_cost",
            data_schema=_build_entity_schema(),
        )

    async def async_step_device_energy_cost_naming(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect names and create the Device Energy Cost entry."""
        await self.async_set_unique_id(_module_unique_id(MODULE_DEVICE_ENERGY_COST))
        self._abort_if_unique_id_configured()

        if user_input is not None:
            entity_names: dict[str, str] = {}

            for i, entity_id in enumerate(self._selected_entity_ids):
                value = user_input.get(_entity_name_key(i), "").strip()
                if value:
                    entity_names[entity_id] = value

            return self.async_create_entry(
                title="Device Energy Cost",
                data={
                    CONF_MODULE: MODULE_DEVICE_ENERGY_COST,
                    CONF_ENERGY_ENTITY_IDS: self._selected_entity_ids,
                    CONF_ENTITY_NAMES: entity_names,
                },
            )

        return self.async_show_form(
            step_id="device_energy_cost_naming",
            data_schema=_build_naming_schema(self.hass, self._selected_entity_ids),
        )

    async def async_step_weather(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_abort(reason="not_implemented")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self._get_reconfigure_entry()
        module = entry.data.get(CONF_MODULE)

        if module == MODULE_DEVICE_ENERGY_COST:
            return self.async_abort(reason="reconfigure_not_supported")

        return self.async_abort(reason="not_implemented")


class HASGPOptionsFlow(OptionsFlowWithReload):
    def __init__(self) -> None:
        self._selected_entity_ids: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        module = self.config_entry.data.get(CONF_MODULE)

        if module == MODULE_DEVICE_ENERGY_COST:
            return await self.async_step_device_energy_cost_options(user_input)

        return self.async_abort(reason="not_implemented")

    async def async_step_device_energy_cost_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current_entity_ids = list(
            self.config_entry.options.get(
                CONF_ENERGY_ENTITY_IDS,
                self.config_entry.data.get(CONF_ENERGY_ENTITY_IDS, []),
            )
        )

        if user_input is not None:
            self._selected_entity_ids = list(user_input[CONF_ENERGY_ENTITY_IDS])
            return await self.async_step_device_energy_cost_options_naming()

        return self.async_show_form(
            step_id="device_energy_cost_options",
            data_schema=_build_entity_schema(
                {CONF_ENERGY_ENTITY_IDS: current_entity_ids}
            ),
        )

    async def async_step_device_energy_cost_options_naming(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        existing_names = dict(
            self.config_entry.options.get(
                CONF_ENTITY_NAMES,
                self.config_entry.data.get(CONF_ENTITY_NAMES, {}),
            )
        )

        if user_input is not None:
            entity_names: dict[str, str] = {}

            for i, entity_id in enumerate(self._selected_entity_ids):
                value = user_input.get(_entity_name_key(i), "").strip()
                if value:
                    entity_names[entity_id] = value

            return self.async_create_entry(
                title="",
                data={
                    CONF_ENERGY_ENTITY_IDS: self._selected_entity_ids,
                    CONF_ENTITY_NAMES: entity_names,
                },
            )

        return self.async_show_form(
            step_id="device_energy_cost_options_naming",
            data_schema=_build_naming_schema(
                self.hass,
                self._selected_entity_ids,
                existing_names,
            ),
        )