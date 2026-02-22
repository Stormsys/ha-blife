"""Shared API helpers for the BLife Packages integration."""

from __future__ import annotations

from typing import Any

from .const import API_BASE_URL


def build_login_headers(device_id: str) -> dict[str, str]:
    """Build headers for the BLife login endpoint."""
    return {
        "App-Path": "typeID:sign-in, appID:sign-in",
        "Accept": "application/json, text/plain, */*",
        "Sec-Fetch-Site": "cross-site",
        "Accept-Language": "en-GB,en;q=0.9",
        "Sec-Fetch-Mode": "cors",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "app://localhost",
        "DeviceID": device_id,
        "Authorization-Type": "Bearer",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ),
        "Sec-Fetch-Dest": "empty",
    }


def build_data_headers(device_id: str, token: str) -> dict[str, str]:
    """Build headers for BLife data endpoints."""
    return {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Sec-Fetch-Site": "cross-site",
        "Accept-Language": "en-GB,en;q=0.9",
        "Sec-Fetch-Mode": "cors",
        "App-Path": "typeID:my-deliveries, appID:my-deliveries",
        "Origin": "app://localhost",
        "DeviceID": device_id,
        "Authorization-Type": "Bearer",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ),
        "Sec-Fetch-Dest": "empty",
    }


def build_login_payload(
    username: str, password: str, device_id: str
) -> dict[str, Any]:
    """Build the login request payload."""
    return {
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


PACKAGES_URL = (
    f"{API_BASE_URL}/my-deliveries/data-query/packages"
    "?$top=25&$skip=0&$orderBy=refNumber%20desc"
)
LOGIN_URL = f"{API_BASE_URL}/account/login"
