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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, DEFAULT_NAME, AUTH_URL, BASE_URL, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Quandify sensor."""
    
    coordinator = QuandifyDataCoordinator(hass, config_entry.data)
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([QuandifyWaterSensor(coordinator)])

class QuandifyDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Quandify data."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize."""
        self.account_id = config["account_id"]
        self.password = config[CONF_PASSWORD]
        self.organization_id = config["organization_id"]
        self._token = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )

    async def _async_update_data(self) -> float:
        """Fetch data from Quandify API."""
        try:
            # Get current day's data (from midnight to now)
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            from_timestamp = int(start_of_day.timestamp())
            to_timestamp = int(now.timestamp())
            
            # Authenticate if no token or token expired
            if not self._token:
                self._token = await self._authenticate()
                if not self._token:
                    raise UpdateFailed("Authentication failed")
            
            # Fetch consumption data
            data = await self._get_consumption_data(from_timestamp, to_timestamp)
            if data is None:
                # Try re-authenticating once
                _LOGGER.warning("Data fetch failed, trying to re-authenticate")
                self._token = await self._authenticate()
                if self._token:
                    data = await self._get_consumption_data(from_timestamp, to_timestamp)
                
            if data is None:
                raise UpdateFailed("Failed to fetch consumption data")
                
            return data
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def _authenticate(self) -> str | None:
        """Authenticate with Quandify API."""
        payload = {"account_id": self.account_id, "password": self.password}
        headers = {"Content-Type": "application/json"}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(AUTH_URL, json=payload, headers=headers, timeout=10)
            )
            
            if response.status_code == 200:
                return response.json().get("id_token")
            else:
                _LOGGER.error("Authentication failed: %s", response.text)
                return None
                
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
                lambda: requests.get(url, headers=headers, params=params, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                if "aggregate" in data and "total" in data["aggregate"] and "totalVolume" in data["aggregate"]["total"]:
                    return float(data["aggregate"]["total"]["totalVolume"])
                else:
                    _LOGGER.error("Unexpected data structure in response")
                    return None
            else:
                _LOGGER.error("API request failed: %s", response.text)
                return None
                
        except Exception as e:
            _LOGGER.error("Error fetching consumption data: %s", str(e))
            return None

class QuandifyWaterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Quandify water consumption sensor."""

    def __init__(self, coordinator: QuandifyDataCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = DEFAULT_NAME
        self._attr_unique_id = f"quandify_{coordinator.organization_id}_water"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_icon = "mdi:water"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.organization_id)},
            "name": "Quandify Water Monitor",
            "manufacturer": "Quandify",
            "model": "Water Consumption Monitor",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "organization_id": self.coordinator.organization_id,
            "last_updated": datetime.now().isoformat(),
            "unit": "liters",
        }
