Le contenu est généré par les utilisateurs et non vérifié.
"""Intuis Connect integration for Home Assistant."""
import logging
from datetime import timedelta
import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_BASE_URL,
    API_TOKEN,
    API_HOMESDATA,
    API_HOMESTATUS,
    API_SETTEMP,
    CLIENT_ID,
    CLIENT_SECRET,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.CLIMATE]


class IntuisAPI:
    """Handle Intuis Connect API."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession):
        """Initialize API."""
        self.username = username
        self.password = password
        self.session = session
        self.token = None
        self.home_id = None

    async def authenticate(self):
        """Authenticate with Intuis API."""
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "user_prefix": "muller",
            "scope": "read_muller write_muller",
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    f"{API_BASE_URL}{API_TOKEN}",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                
                if response.status != 200:
                    _LOGGER.error("Auth failed: %s", response.status)
                    return False
                
                result = await response.json()
                self.token = result.get("access_token")
                _LOGGER.info("Authentication successful")
                return True
                
        except Exception as err:
            _LOGGER.error("Auth error: %s", err)
            return False

    async def get_data(self):
        """Get radiator data."""
        if not self.token:
            if not await self.authenticate():
                raise UpdateFailed("Authentication failed")

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            # Get home data
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    f"{API_BASE_URL}{API_HOMESDATA}",
                    headers=headers,
                )
                
                if response.status == 401:
                    await self.authenticate()
                    return await self.get_data()
                
                if response.status != 200:
                    raise UpdateFailed(f"API error: {response.status}")
                
                homes = await response.json()
                self.home_id = homes["body"]["homes"][0]["id"]

            # Get status
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    f"{API_BASE_URL}{API_HOMESTATUS}",
                    data={"home_id": self.home_id},
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                
                if response.status != 200:
                    raise UpdateFailed(f"Status error: {response.status}")
                
                status = await response.json()
                rooms = status["body"]["home"]["rooms"]
                
                return [
                    {
                        "id": room["id"],
                        "name": room.get("name", f"Radiateur {room['id'][:8]}"),
                        "home_id": self.home_id,
                        "current_temp": room.get("therm_measured_temperature"),
                        "target_temp": room.get("therm_setpoint_temperature"),
                        "mode": room.get("therm_setpoint_mode"),
                    }
                    for room in rooms
                ]

        except Exception as err:
            _LOGGER.error("Get data error: %s", err)
            raise UpdateFailed(f"Error: {err}")

    async def set_temperature(self, room_id: str, temperature: float):
        """Set room temperature."""
        if not self.token or not self.home_id:
            raise UpdateFailed("Not authenticated")

        data = {
            "home_id": self.home_id,
            "room_id": room_id,
            "mode": "manual",
            "temp": str(temperature),
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    f"{API_BASE_URL}{API_SETTEMP}",
                    json=data,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                )
                
                _LOGGER.debug("Set temp response: %s", response.status)
                return response.status == 200

        except Exception as err:
            _LOGGER.error("Set temp error: %s", err)
            return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    session = async_get_clientsession(hass)
    api = IntuisAPI(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session,
    )

    # Test authentication
    if not await api.authenticate():
        return False

    # Create coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=api.get_data,
        update_interval=timedelta(seconds=SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
