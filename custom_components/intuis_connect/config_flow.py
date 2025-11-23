Le contenu est généré par les utilisateurs et non vérifié.
"""Config flow for Intuis Connect."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IntuisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        errors = {}

        if user_input is not None:
            from . import IntuisAPI

            session = async_get_clientsession(self.hass)
            api = IntuisAPI(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                session,
            )

            if await api.authenticate():
                return self.async_create_entry(
                    title=f"Intuis ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
