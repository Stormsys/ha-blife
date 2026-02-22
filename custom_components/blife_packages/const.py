"""Constants for the BLife Packages integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "blife_packages"

CONF_DEVICE_ID: Final = "device_id"

# API Configuration
API_BASE_URL: Final = "https://api-community.ballymorelife.com"
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)

# Sensor types
SENSOR_PACKAGES_COUNT: Final = "packages_ready_to_collect"
SENSOR_LAST_PACKAGE_REF: Final = "last_package_ref_number"

# Attributes
ATTR_PACKAGES: Final = "packages"
