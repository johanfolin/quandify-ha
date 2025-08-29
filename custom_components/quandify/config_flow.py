"""Config flow for Quandify integration."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_ORGANIZATION_ID, AUTH_URL

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_ID): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ORGANIZATION_ID): cv.string,
    }
)

def is_valid_guid(guid: str) -> bool:
    """Check if string is a valid GUID format."""
    guid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE
    )
    return bool(guid_pattern.match(guid))

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Validate GUID formats
    if not is_valid_guid(data[CONF_ACCOUNT_ID]):
        raise InvalidGuid("account_id")
    
    if not is_valid_guid(data[CONF_ORGANIZATION_ID]):
        raise InvalidGuid("organization_id")
    
    # Test authentication
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                AUTH_URL,
                json={
                    "account_id": data[CONF_ACCOUNT_ID],
                    "password": data[CONF_PASSWORD]
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        )
        
        if response.status_code != 200:
            if response.status_code == 401:
                raise InvalidAuth()
            else:
                raise CannotConnect()
        
        token = response.json().get("id_token")
        if not token:
            raise InvalidAuth()
            
    except requests.exceptions.RequestException as exc:
        _LOGGER.error("Error connecting to Quandify API: %s", exc)
        raise CannotConnect() from exc
    except Exception as exc:
        _LOGGER.error("Unexpected error during validation: %s", exc)
        raise CannotConnect() from exc
    
    # Return info that you want to store in the config entry.
    return {"title": f"Quandify ({data[CONF_ACCOUNT_ID][:8]}...)"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Quandify."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_ACCOUNT_ID])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidGuid as exc:
                errors[exc.field] = "invalid_guid"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "account_id_example": "12345678-1234-5678-9012-123456789012",
                "org_id_example": "87654321-4321-8765-2109-876543210987",
            },
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidGuid(HomeAssistantError):
    """Error to indicate invalid GUID format."""
    
    def __init__(self, field: str) -> None:
        """Initialize the error."""
        super().__init__()
        self.field = field
