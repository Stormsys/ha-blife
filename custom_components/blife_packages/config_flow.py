"""Config flow for BLife Packages integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LOGIN_URL, build_login_headers, build_login_payload
from .const import CONF_DEVICE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_DEVICE_ID): str,
    }
)


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    device_id = data[CONF_DEVICE_ID]

    _LOGGER.debug(
        "Validating credentials for user %s with device %s", username, device_id
    )

    headers = build_login_headers(device_id)
    payload = build_login_payload(username, password, device_id)
    session = async_get_clientsession(hass)

    try:
        async with session.post(
            LOGIN_URL, headers=headers, json=payload
        ) as response:
            if response.status == 401:
                raise InvalidAuth
            if response.status != 200:
                _LOGGER.error(
                    "Login failed with status %d", response.status
                )
                raise CannotConnect

            try:
                result = await response.json()
            except (aiohttp.ContentTypeError, ValueError) as err:
                _LOGGER.error("Invalid response from API: %s", err)
                raise CannotConnect from err

            token = response.headers.get("U-Set-Token")
            if not token:
                _LOGGER.warning("No U-Set-Token header in response")

            user_details = (result.get("user") or {}).get("details") or {}
            firstname = user_details.get("firstName", "").strip()
            if not firstname:
                firstname = username.split("@")[0].split(".")[0].capitalize()

            return {
                "title": f"BLife - {firstname}",
                "firstname": firstname,
                "token": token,
            }
    except aiohttp.ClientError as err:
        _LOGGER.error("Connection error during login: %s", err)
        raise CannotConnect from err


class BLifePackagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLife Packages."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                user_input["firstname"] = info["firstname"]
                if info.get("token"):
                    user_input["token"] = info["token"]
                return self.async_create_entry(
                    title=info["title"], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            try:
                info = await validate_input(
                    self.hass,
                    {
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_DEVICE_ID: reauth_entry.data[CONF_DEVICE_ID],
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        "firstname": info["firstname"],
                        "token": info.get("token"),
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
