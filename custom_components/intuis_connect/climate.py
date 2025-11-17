"""Climate platform for Intuis Connect."""
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Intuis Connect climate entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    entities = []
    for device in coordinator.data:
        entities.append(IntuisConnectClimate(coordinator, api, device))

    async_add_entities(entities)


class IntuisConnectClimate(CoordinatorEntity, ClimateEntity):
    """Representation of an Intuis Connect climate device."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    def __init__(self, coordinator, api, device):
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._attr_unique_id = f"intuis_{device['id']}"
        self._attr_name = device.get("name", f"Radiateur {device['id']}")
        self._attr_min_temp = DEFAULT_MIN_TEMP
        self._attr_max_temp = DEFAULT_MAX_TEMP

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device["id"])},
            "name": self._attr_name,
            "manufacturer": "Intuis",
            "model": "Connect",
        }

    @property
    def current_temperature(self):
        """Return the current temperature."""
        for device in self.coordinator.data:
            if device["id"] == self._device["id"]:
                return device.get("current_temperature")
        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        for device in self.coordinator.data:
            if device["id"] == self._device["id"]:
                return device.get("target_temperature")
        return None

    @property
    def hvac_mode(self):
        """Return current operation mode."""
        for device in self.coordinator.data:
            if device["id"] == self._device["id"]:
                mode = device.get("mode", "schedule")
                if mode == "frostguard":
                    return HVACMode.OFF
                return HVACMode.HEAT
        return HVACMode.HEAT

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        success = await self._api.set_temperature(
            self._device["home_id"],
            self._device["id"],
            temperature
        )
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature for %s", self._attr_name)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            success = await self._api.set_mode(
                self._device["home_id"],
                self._device["id"],
                "frostguard"
            )
        elif hvac_mode == HVACMode.HEAT:
            success = await self._api.set_mode(
                self._device["home_id"],
                self._device["id"],
                "schedule"
            )
        else:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set HVAC mode for %s", self._attr_name)

    async def async_turn_on(self):
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
