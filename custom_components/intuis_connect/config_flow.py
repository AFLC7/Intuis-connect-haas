"""Config flow for Intuis Connect integration."""
import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_BASE_URL, API_LOGIN, CLIENT_ID, CLIENT_SECRET

_LOGGER = logging.getLogger(__name__)


class IntuisConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Intuis Connect."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate credentials
            session = async_get_clientsession(self.hass)
            
            try:
                data = {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "password",
                    "username": user_input[CONF_USERNAME],
                    "password": user_input[CONF_PASSWORD],
                    "user_prefix": "muller",
                    "scope": "read_muller write_muller",
                }
                
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                
                async with session.post(
                    f"{API_BASE_URL}{API_LOGIN}",
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        # Success - create entry
                        return self.async_create_entry(
                            title=f"Intuis Connect ({user_input[CONF_USERNAME]})",
                            data=user_input,
                        )
                    elif response.status == 401:
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
