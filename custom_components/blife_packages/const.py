"""Constants for the BLife Packages integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "blife_packages"

# Configuration keys
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_DEVICE_ID: Final = "device_id"

# API Configuration
API_BASE_URL: Final = "https://api-community.ballymorelife.com"
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)

# Sensor types
SENSOR_PACKAGES_COUNT: Final = "packages_ready_to_collect"
SENSOR_LAST_PACKAGE_REF: Final = "last_package_ref_number"

# Attributes
ATTR_PACKAGES: Final = "packages"
ATTR_PACKAGE_ID: Final = "package_id"
ATTR_PACKAGE_CODE: Final = "code"
ATTR_PACKAGE_DESCRIPTION: Final = "description"
ATTR_PACKAGE_ARRIVED_AT: Final = "arrived_at"
ATTR_PACKAGE_STATUS: Final = "status"
ATTR_FIRSTNAME: Final = "firstname"

