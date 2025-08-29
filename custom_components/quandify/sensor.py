"""Quandify water consumption sensor."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import requests
from requests.exceptions import RequestException

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    AUTH_URL,
    BASE_URL,
    UPDATE_INTERVAL_MINUTES,
    CONF_ACCOUNT_ID,
    CONF_ORGANIZATION_ID,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Quandify sensor."""
    
    config = hass.data[DOMAIN][config_entry.entry_id]
    
    coordinator = QuandifyDataCoordinator(hass, config)
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([QuandifyWaterSensor(coordinator, config_entry)])

class QuandifyDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Quandify data."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        self.account_id = config[CONF_ACCOUNT_ID]
        self.password = config[CONF_PASSWORD]
        self.organization_id = config[CONF_ORGANIZATION_ID]
        self._token = None
        self._token_expires = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> float:
        """Fetch data from Quandify API."""
        try:
            # Calculate time range for current day
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            from_timestamp = int(start_of_day.timestamp())
            to_timestamp = int(now.timestamp())
            
            _LOGGER.debug(
                "Fetching data for period: %s to %s",
                start_of_day.isoformat(),
                now.isoformat()
            )
            
            # Ensure we have a valid token
            token = await self._ensure_token()
            if not token:
                raise UpdateFailed("Failed to authenticate with Quandify API")
            
            # Fetch consumption data
            data = await self._get_consumption_data(from_timestamp, to_timestamp)
            
            if data is None:
                # Token might be expired, try once more with new token
                _LOGGER.warning("Data fetch failed, attempting re-authentication")
                self._token = None
                token = await self._ensure_token()
                if token:
                    data = await self._get_consumption_data(from_timestamp, to_timestamp)
                
                if data is None:
                    raise UpdateFailed("Failed to fetch consumption data after re-authentication")
            
            _LOGGER.debug("Successfully fetched consumption data: %s", data)
            return data
            
        except Exception as err:
            _LOGGER.error("Error updating Quandify data: %s", err)
            raise UpdateFailed(f"Error communicating with Quandify API: {err}") from err

    async def _ensure_token(self) -> str | None:
        """Ensure we have a valid authentication token."""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token
        
        return await self._authenticate()

    async def _authenticate(self) -> str | None:
        """Authenticate with Quandify API."""
        payload = {
            "account_id": self.account_id,
            "password": self.password
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    AUTH_URL,
                    json=payload,
                    headers=headers,
                    timeout=15
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("id_token")
                if token:
                    self._token = token
                    # Set token expiry to 23 hours from now (tokens typically last 24h)
                    self._token_expires = datetime.now() + timedelta(hours=23)
                    _LOGGER.debug("Authentication successful")
                    return token
                else:
                    _LOGGER.error("No token in authentication response")
            else:
                _LOGGER.error(
                    "Authentication failed: HTTP %s - %s",
                    response.status_code,
                    response.text
                )
                
        except Exception as e:
            _LOGGER.error("Error during authentication: %s", str(e))
            
        return None

    async def _get_consumption_data(self, from_ts: int, to_ts: int) -> float | None:
        """Fetch consumption data from API."""
        url = f"{BASE_URL}/organization/{self.organization_id}/nodes/detailed-consumption"
        params = {
            "from": from_ts,
            "to": to_ts,
            "truncate": "day"
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Navigate to the totalVolume data
                if (
                    "aggregate" in data
                    and "total" in data["aggregate"]
                    and "totalVolume" in data["aggregate"]["total"]
                ):
                    volume = data["aggregate"]["total"]["totalVolume"]
                    return float(volume) if volume is not None else 0.0
                else:
                    _LOGGER.error("Unexpected API response structure: %s", list(data.keys()) if isinstance(data, dict) else type(data))
                    return None
            else:
                _LOGGER.error(
                    "API request failed: HTTP %s - %s",
                    response.status_code,
                    response.text
                )
                return None
                
        except Exception as e:
            _LOGGER.error("Error fetching consumption data: %s", str(e))
            return None

class QuandifyWaterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Quandify water consumption sensor."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: QuandifyDataCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self.config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{coordinator.organization_id}_water_consumption"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_icon = "mdi:water"
        self._attr_suggested_display_precision = 1
        
        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.organization_id)},
            name="Quandify Water Monitor",
            manufacturer="Quandify",
            model="Water Consumption Monitor",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is not None:
            return round(float(self.coordinator.data), 2)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "organization_id": self.coordinator.organization_id,
            "integration": DOMAIN,
        }
        
        if self.coordinator.last_update_success_time:
            attrs["last_updated"] = self.coordinator.last_update_success_time.isoformat()
            
        return attrs
