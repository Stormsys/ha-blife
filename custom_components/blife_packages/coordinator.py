"""Data coordinator for BLife Packages integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LOGIN_URL,
    PACKAGES_URL,
    build_data_headers,
    build_login_headers,
    build_login_payload,
)
from .const import (
    CONF_DEVICE_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Package:
    """Representation of a package."""

    package_id: str
    ref_number: str
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
            "is_collection_required": self.is_collection_required,
            "latest_action": self.latest_action,
            "created_date": (
                self.created_date.isoformat() if self.created_date else None
            ),
            "latest_action_date": (
                self.latest_action_date.isoformat()
                if self.latest_action_date
                else None
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
    def uncollected_packages(self) -> list[Package]:
        """Return packages that are ready to collect."""
        return [
            p
            for p in self.packages
            if p.latest_action != "collected" and p.created_date is not None
        ]

    @property
    def packages_ready_to_collect(self) -> int:
        """Return count of packages ready to collect."""
        return len(self.uncollected_packages)

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
        self._username = config_entry.data[CONF_USERNAME]
        self._password = config_entry.data[CONF_PASSWORD]
        self._device_id = config_entry.data[CONF_DEVICE_ID]
        self.firstname = config_entry.data.get("firstname", "User")
        self._token: str | None = config_entry.data.get("token")
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> BLifePackagesData:
        """Fetch data from API."""
        try:
            return await self._fetch_packages_data()
        except (ConfigEntryAuthFailed, UpdateFailed):
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching packages data: {err}") from err

    async def _fetch_packages_data(self) -> BLifePackagesData:
        """Fetch packages data from the BLife API."""
        if not self._token:
            await self._authenticate()

        headers = build_data_headers(self._device_id, self._token)

        try:
            async with self._session.get(
                PACKAGES_URL, headers=headers
            ) as response:
                if response.status == 401:
                    _LOGGER.warning("Token expired, re-authenticating")
                    await self._authenticate()
                    headers = build_data_headers(self._device_id, self._token)
                    async with self._session.get(
                        PACKAGES_URL, headers=headers
                    ) as retry_response:
                        if retry_response.status == 401:
                            raise ConfigEntryAuthFailed(
                                "Authentication failed. Please reconfigure."
                            )
                        if retry_response.status != 200:
                            raise UpdateFailed(
                                f"API returned {retry_response.status}"
                            )
                        data = await self._parse_json(retry_response)
                elif response.status != 200:
                    raise UpdateFailed(
                        f"API returned {response.status}"
                    )
                else:
                    data = await self._parse_json(response)

                _LOGGER.debug("Fetched %d packages", len(data.get("list", [])))
                return self._parse_packages_response(data)
        except (ConfigEntryAuthFailed, UpdateFailed):
            raise
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

    async def _authenticate(self) -> None:
        """Authenticate and get a new token."""
        headers = build_login_headers(self._device_id)
        payload = build_login_payload(
            self._username, self._password, self._device_id
        )

        try:
            async with self._session.post(
                LOGIN_URL, headers=headers, json=payload
            ) as response:
                if response.status == 401:
                    raise ConfigEntryAuthFailed("Invalid credentials")
                if response.status != 200:
                    raise UpdateFailed(
                        f"Login failed with status {response.status}"
                    )

                token = response.headers.get("U-Set-Token")
                if not token:
                    raise UpdateFailed("No token received from login")

                self._token = token
                _LOGGER.debug("Successfully authenticated")
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Connection error during login: {err}") from err

    @staticmethod
    async def _parse_json(response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Parse JSON response with error handling."""
        try:
            data = await response.json()
        except (aiohttp.ContentTypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid JSON response from API: {err}"
            ) from err

        if not isinstance(data, dict):
            raise UpdateFailed("Unexpected API response format")
        return data

    def _parse_packages_response(self, data: dict[str, Any]) -> BLifePackagesData:
        """Parse the API response into BLifePackagesData."""
        packages = []
        package_list = data.get("list", [])

        for pkg_data in package_list:
            created_date = None
            created_model = pkg_data.get("createdDateModel") or {}
            if created_ms := created_model.get("ms"):
                created_date = datetime.fromtimestamp(
                    created_ms / 1000, tz=timezone.utc
                )

            latest_action_date = None
            action_model = pkg_data.get("latestActionDateModel") or {}
            if action_ms := action_model.get("ms"):
                latest_action_date = datetime.fromtimestamp(
                    action_ms / 1000, tz=timezone.utc
                )

            package = Package(
                package_id=pkg_data.get("id", ""),
                ref_number=pkg_data.get("refNumber", ""),
                is_collection_required=pkg_data.get(
                    "isCollectionRequired", False
                ),
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
            last_updated=datetime.now(tz=timezone.utc),
        )
