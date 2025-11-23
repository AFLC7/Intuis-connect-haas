"""The Intuis Connect integration."""
import logging
import aiohttp
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    API_BASE_URL,
    API_LOGIN,
    API_HOMESDATA,
    API_HOMESTATUS,
    API_SETROOMTHERMPOINT,
    CLIENT_ID,
    CLIENT_SECRET,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]


class IntuisConnectAPI:
    """Class to communicate with Intuis Connect API."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession):
        """Initialize the API."""
        self.username = username
        self.password = password
        self.session = session
        self.token = None

    async def login(self):
        """Login to Intuis Connect via OAuth."""
        try:
            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "user_prefix": "muller",
                "scope": "read_muller write_muller",
            }
            
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with self.session.post(
                f"{API_BASE_URL}{API_LOGIN}",
                data=data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("access_token")
                    return True
                else:
                    _LOGGER.error("Login failed with status %s", response.status)
                    return False
        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def get_devices(self):
        """Get all homes and rooms data."""
        if not self.token:
            await self.login()

        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Get homes data
            async with self.session.get(
                f"{API_BASE_URL}{API_HOMESDATA}", headers=headers
            ) as response:
                if response.status == 200:
                    homes_data = await response.json()
                    
                    if not homes_data.get("body", {}).get("homes"):
                        return []
                    
                    home = homes_data["body"]["homes"][0]
                    home_id = home["id"]
                    
                    # Get current status
                    status_data = {"home_id": home_id}
                    headers_status = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                    
                    async with self.session.post(
                        f"{API_BASE_URL}{API_HOMESTATUS}",
                        data=status_data,
                        headers=headers_status,
                    ) as status_response:
                        if status_response.status == 200:
                            status = await status_response.json()
                            rooms = status.get("body", {}).get("home", {}).get("rooms", [])
                            
                            # Format rooms data for Home Assistant
                            devices = []
                            for room in rooms:
                                devices.append({
                                    "id": room["id"],
                                    "name": room.get("name", "Radiateur"),
                                    "home_id": home_id,
                                    "current_temperature": room.get("therm_measured_temperature"),
                                    "target_temperature": room.get("therm_setpoint_temperature"),
                                    "mode": room.get("therm_setpoint_mode"),
                                })
                            
                            return devices
                        else:
                            _LOGGER.error("Failed to get status: %s", status_response.status)
                            return []
                            
                elif response.status == 401:
                    await self.login()
                    return await self.get_devices()
                else:
                    _LOGGER.error("Failed to get devices: %s", response.status)
                    return []
        except Exception as err:
            _LOGGER.error("Error getting devices: %s", err)
            return []

    async def set_temperature(self, home_id: str, room_id: str, temperature: float):
        """Set target temperature for a room."""
        if not self.token:
            await self.login()

        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json;charset=utf-8"
            }
            
            payload = {
                "home": {
                    "id": home_id,
                    "rooms": [
                        {
                            "id": room_id,
                            "therm_setpoint_mode": "manual",
                            "therm_setpoint_temperature": temperature
                        }
                    ]
                }
            }
            
            async with self.session.post(
                f"{API_BASE_URL}{API_SETROOMTHERMPOINT}",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    _LOGGER.info(f"Temperature set successfully to {temperature}°C for room {room_id}")
                    return True
                else:
                    response_text = await response.text()
                    _LOGGER.error(f"Failed to set temperature. Status: {response.status}, Response: {response_text}")
                    return False
        except Exception as err:
            _LOGGER.error("Error setting temperature: %s", err)
            return False

    async def set_mode(self, home_id: str, room_id: str, mode: str):
        """Set heating mode for a room (schedule, manual, away, hg)."""
        if not self.token:
            await self.login()

        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json;charset=utf-8"
            }
            
            payload = {
                "home": {
                    "id": home_id,
                    "rooms": [
                        {
                            "id": room_id,
                            "therm_setpoint_mode": mode
                        }
                    ]
                }
            }
            
            async with self.session.post(
                f"{API_BASE_URL}{API_SETROOMTHERMPOINT}",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    _LOGGER.info(f"Mode set successfully to {mode} for room {room_id}")
                    return True
                else:
                    response_text = await response.text()
                    _LOGGER.error(f"Failed to set mode. Status: {response.status}, Response: {response_text}")
                    return False
        except Exception as err:
            _LOGGER.error("Error setting mode: %s", err)
            return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intuis Connect from a config entry."""
    session = async_get_clientsession(hass)
    api = IntuisConnectAPI(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        session,
    )

    # Login
    if not await api.login():
        _LOGGER.error("Failed to login to Intuis Connect")
        return False

    # Create coordinator
    async def async_update_data():
        """Fetch data from API."""
        try:
            devices = await api.get_devices()
            return devices
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
