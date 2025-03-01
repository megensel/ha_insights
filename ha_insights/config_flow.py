"""Config flow for HA Insights integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any, Dict, List, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_SCAN_INTERVAL,
    CONF_EXCLUDED_ENTITIES,
    CONF_TRACKED_DOMAINS,
    CONF_MIN_STATE_CHANGES,
    CONF_MAX_SUGGESTIONS,
    CONF_PURGE_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MIN_STATE_CHANGES,
    DEFAULT_MAX_SUGGESTIONS,
    DEFAULT_PURGE_DAYS,
    DEFAULT_TRACKED_DOMAINS,
    AVAILABLE_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


class HAInsightsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Insights."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # Validate the inputs
            return self.async_create_entry(
                title=DEFAULT_NAME,
                data={},
                options=user_input,
            )

        # Show form if no user input
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL, 
                    default=DEFAULT_SCAN_INTERVAL
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=15, 
                        max=1440, 
                        step=15, 
                        unit_of_measurement="minutes",
                        mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_TRACKED_DOMAINS, 
                    default=DEFAULT_TRACKED_DOMAINS
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": domain, "label": domain.capitalize()}
                            for domain in AVAILABLE_DOMAINS
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=False,
                    )
                ),
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return HAInsightsOptionsFlow(config_entry)


class HAInsightsOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the HA Insights integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Update with new options
            return self.async_create_entry(title="", data=user_input)

        # Fill options with current values or defaults
        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        tracked_domains = self.config_entry.options.get(
            CONF_TRACKED_DOMAINS, DEFAULT_TRACKED_DOMAINS
        )
        min_state_changes = self.config_entry.options.get(
            CONF_MIN_STATE_CHANGES, DEFAULT_MIN_STATE_CHANGES
        )
        max_suggestions = self.config_entry.options.get(
            CONF_MAX_SUGGESTIONS, DEFAULT_MAX_SUGGESTIONS
        )
        purge_days = self.config_entry.options.get(
            CONF_PURGE_DAYS, DEFAULT_PURGE_DAYS
        )

        # Get entities for exclusion list
        excluded_entities = self.config_entry.options.get(CONF_EXCLUDED_ENTITIES, [])

        # Show advanced options form
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL, 
                    default=scan_interval
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=15, 
                        max=1440, 
                        step=15, 
                        unit_of_measurement="minutes",
                        mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_TRACKED_DOMAINS, 
                    default=tracked_domains
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": domain, "label": domain.capitalize()}
                            for domain in AVAILABLE_DOMAINS
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                        custom_value=False,
                    )
                ),
                vol.Optional(
                    CONF_EXCLUDED_ENTITIES, 
                    default=excluded_entities
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_MIN_STATE_CHANGES, 
                    default=min_state_changes
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, 
                        max=500, 
                        step=5,
                        mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAX_SUGGESTIONS, 
                    default=max_suggestions
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, 
                        max=50, 
                        step=1,
                        mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_PURGE_DAYS, 
                    default=purge_days
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=7, 
                        max=365, 
                        step=1, 
                        unit_of_measurement="days",
                        mode=NumberSelectorMode.BOX
                    )
                ),
            }),
            errors=errors,
        ) 