"""Data coordinator for BLife Packages integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE_URL,
    CONF_DEVICE_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Package:
    """Representation of a package."""

    package_id: str
    ref_number: str  # The code used to collect the package
    is_collection_required: bool
    latest_action: str
    created_date: datetime | None = None
    latest_action_date: datetime | None = None
    addressed_to_unit: str | None = None
    sender_name: str | None = None
    courier_name: str | None = None
    internal_number: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert package to dictionary for attributes."""
        return {
            "package_id": self.package_id,
            "ref_number": self.ref_number,
            "code": self.ref_number,  # Alias for compatibility
            "is_collection_required": self.is_collection_required,
            "latest_action": self.latest_action,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "latest_action_date": (
                self.latest_action_date.isoformat() if self.latest_action_date else None
            ),
            "addressed_to_unit": self.addressed_to_unit,
            "sender_name": self.sender_name,
            "courier_name": self.courier_name,
            "internal_number": self.internal_number,
        }


@dataclass
class BLifePackagesData:
    """Data class for BLife packages state."""

    firstname: str
    packages: list[Package] = field(default_factory=list)
    last_updated: datetime | None = None

    @property
    def packages_ready_to_collect(self) -> int:
        """Return count of packages ready to collect."""
        return len([
            p for p in self.packages
            if p.latest_action != "collected" and p.created_date is not None
        ])

    @property
    def packages_list(self) -> list[dict[str, Any]]:
        """Return list of packages as dictionaries."""
        return [p.to_dict() for p in self.packages]


class BLifePackagesCoordinator(DataUpdateCoordinator[BLifePackagesData]):
    """Coordinator for fetching BLife packages data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=config_entry,
        )
        self.username = config_entry.data[CONF_USERNAME]
        self.password = config_entry.data[CONF_PASSWORD]
        self.device_id = config_entry.data[CONF_DEVICE_ID]
        self.firstname = config_entry.data.get("firstname", "User")
        self._token = config_entry.data.get("token")

    async def _async_update_data(self) -> BLifePackagesData:
        """Fetch data from API."""
        try:
            return await self._fetch_packages_data()
        except Exception as err:
            raise UpdateFailed(f"Error fetching packages data: {err}") from err

    async def _fetch_packages_data(self) -> BLifePackagesData:
        """Fetch packages data from the BLife API."""
        # Re-authenticate if we don't have a token
        if not self._token:
            await self._authenticate()

        headers = {
            "Host": "api-community.ballymorelife.com",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self._token}",
            "Sec-Fetch-Site": "cross-site",
            "Accept-Language": "en-GB,en;q=0.9",
            "Sec-Fetch-Mode": "cors",
            "App-Path": "typeID:my-deliveries, appID:my-deliveries",
            "Origin": "app://localhost",
            "DeviceID": self.device_id,
            "Authorization-Type": "Bearer",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Sec-Fetch-Dest": "empty",
        }

        url = f"{API_BASE_URL}/my-deliveries/data-query/packages?$top=25&$skip=0&$orderBy=refNumber%20desc"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        # Token expired, try to re-authenticate once
                        _LOGGER.warning("Token expired, re-authenticating...")
                        await self._authenticate()
                        headers["Authorization"] = f"Bearer {self._token}"
                        async with session.get(url, headers=headers) as retry_response:
                            if retry_response.status == 401:
                                raise ConfigEntryAuthFailed(
                                    "Authentication failed. Please reconfigure the integration."
                                )
                            if retry_response.status != 200:
                                raise UpdateFailed(
                                    f"API returned {retry_response.status}"
                                )
                            data = await retry_response.json()
                    elif response.status != 200:
                        raise UpdateFailed(f"API returned {response.status}: {await response.text()}")
                    else:
                        data = await response.json()

                    return self._parse_packages_response(data)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

    async def _authenticate(self) -> None:
        """Authenticate and get a new token."""
        headers = {
            "Host": "api-community.ballymorelife.com",
            "App-Path": "typeID:sign-in, appID:sign-in",
            "Accept": "application/json, text/plain, */*",
            "Sec-Fetch-Site": "cross-site",
            "Accept-Language": "en-GB,en;q=0.9",
            "Sec-Fetch-Mode": "cors",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "app://localhost",
            "DeviceID": self.device_id,
            "Authorization-Type": "Bearer",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Sec-Fetch-Dest": "empty",
        }

        login_data = {
            "UserName": self.username,
            "Password": self.password,
            "RememberMe": True,
            "device": {
                "uuid": self.device_id,
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

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/account/login",
                headers=headers,
                json=login_data,
            ) as response:
                if response.status == 401:
                    raise ConfigEntryAuthFailed("Invalid credentials")
                if response.status != 200:
                    raise UpdateFailed(f"Login failed with status {response.status}")

                token = response.headers.get("U-Set-Token")
                if not token:
                    raise UpdateFailed("No token received from login")
                
                self._token = token
                _LOGGER.debug("Successfully authenticated and obtained new token")

    def _parse_packages_response(self, data: dict[str, Any]) -> BLifePackagesData:
        """Parse the API response into BLifePackagesData."""
        packages = []
        package_list = data.get("list", [])

        for pkg_data in package_list:
            # Parse dates from timestamp (milliseconds)
            created_date = None
            if created_ms := pkg_data.get("createdDateModel", {}).get("ms"):
                created_date = datetime.fromtimestamp(created_ms / 1000)

            latest_action_date = None
            if action_ms := pkg_data.get("latestActionDateModel", {}).get("ms"):
                latest_action_date = datetime.fromtimestamp(action_ms / 1000)

            package = Package(
                package_id=pkg_data.get("id", ""),
                ref_number=pkg_data.get("refNumber", ""),
                is_collection_required=pkg_data.get("isCollectionRequired", False),
                latest_action=pkg_data.get("latestAction", "unknown"),
                created_date=created_date,
                latest_action_date=latest_action_date,
                addressed_to_unit=pkg_data.get("addressedToUnitNumber"),
                sender_name=pkg_data.get("senderName"),
                courier_name=pkg_data.get("courierName"),
                internal_number=pkg_data.get("internalNumber"),
            )
            packages.append(package)

        return BLifePackagesData(
            firstname=self.firstname,
            packages=packages,
            last_updated=datetime.now(),
        )

