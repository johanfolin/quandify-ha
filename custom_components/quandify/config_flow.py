"""Config flow for Quandify integration."""
from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("account_id"): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required("organization_id"): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Quandify."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation - check if account_id looks like a GUID
            account_id = user_input["account_id"]
            if len(account_id) != 36 or account_id.count("-") != 4:
                errors["account_id"] = "invalid_guid"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title="Quandify Water Consumption", 
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "account_id": "12345678-1234-5678-9012-123456789012",
            },
        )
