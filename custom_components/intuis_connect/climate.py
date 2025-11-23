Le contenu est généré par les utilisateurs et non vérifié.
1
"""Climate platform for Intuis Connect."""
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MIN_TEMP, MAX_TEMP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = [
        IntuisClimate(coordinator, api, radiator)
        for radiator in coordinator.data
    ]

    async_add_entities(entities)


class IntuisClimate(CoordinatorEntity, ClimateEntity):
    """Intuis radiator climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT

    def __init__(self, coordinator, api, radiator):
        """Initialize climate entity."""
        super().__init__(coordinator)
        self._api = api
        self._radiator = radiator
        self._attr_unique_id = f"intuis_{radiator['id']}"
        self._attr_name = radiator["name"]
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._radiator["id"])},
            "name": self._radiator["name"],
            "manufacturer": "Intuis",
            "model": "Connect",
        }

    @property
    def current_temperature(self):
        """Return current temperature."""
        for rad in self.coordinator.data:
            if rad["id"] == self._radiator["id"]:
                return rad.get("current_temp")
        return None

    @property
    def target_temperature(self):
        """Return target temperature."""
        for rad in self.coordinator.data:
            if rad["id"] == self._radiator["id"]:
                return rad.get("target_temp")
        return None

    async def async_set_temperature(self, **kwargs):
        """Set new temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        _LOGGER.info("Setting %s to %s°C", self._attr_name, temp)
        
        success = await self._api.set_temperature(self._radiator["id"], temp)
        
        if success:
            _LOGGER.info("Temperature set successfully")
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature")
