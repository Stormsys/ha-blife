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

from .const import API_BASE_URL, CONF_DEVICE_ID, DOMAIN

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


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    device_id = data[CONF_DEVICE_ID]

    _LOGGER.debug(
        "Validating credentials for user %s with device %s", username, device_id
    )

    headers = {
        "Host": "api-community.ballymorelife.com",
        "App-Path": "typeID:sign-in, appID:sign-in",
        "Accept": "application/json, text/plain, */*",
        "Sec-Fetch-Site": "cross-site",
        "Accept-Language": "en-GB,en;q=0.9",
        "Sec-Fetch-Mode": "cors",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "app://localhost",
        "DeviceID": device_id,
        "Authorization-Type": "Bearer",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Sec-Fetch-Dest": "empty",
    }

    login_data = {
        "UserName": username,
        "Password": password,
        "RememberMe": True,
        "device": {
            "uuid": device_id,
            "model": "HomeAssistant",
            "version": "1.0",
            "manufacturer": "HomeAssistant",
            "serial": "unknown",
            "platform": "homeassistant",
            "appPackageId": "com.homeassistant.blife",
            "appVersion": "1.0.0",
            "platformTag": 1,
            "screenLock": True,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/account/login",
                headers=headers,
                json=login_data,
            ) as response:
                if response.status == 401:
                    raise InvalidAuth
                if response.status != 200:
                    _LOGGER.error(
                        "Login failed with status %d: %s",
                        response.status,
                        await response.text(),
                    )
                    raise CannotConnect

                result = await response.json()
                
                # Extract token from U-Set-Token header
                token = response.headers.get("U-Set-Token")
                if not token:
                    _LOGGER.warning("No U-Set-Token header in response")
                
                # Extract firstname from user details
                user_details = result.get("user", {}).get("details", {})
                firstname = user_details.get("firstName", "").strip()
                if not firstname:
                    # Fallback to extracting from email
                    firstname = username.split("@")[0].split(".")[0].capitalize()

                return {
                    "title": f"BLife - {firstname}",
                    "firstname": firstname,
                    "token": token,  # Store token for coordinator
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
            # Check if this device is already configured
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
                # Store firstname and token in the data
                user_input["firstname"] = info["firstname"]
                if "token" in info:
                    user_input["token"] = info["token"]
                return self.async_create_entry(title=info["title"], data=user_input)

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

