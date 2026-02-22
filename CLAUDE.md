# CLAUDE.md

## Project Overview

**BLife Concierge Packages** is a Home Assistant custom integration that tracks packages at a building's concierge desk via the BLife (Ballymore Life) API. It polls the API every 5 minutes and exposes sensor entities showing package counts and details.

- **Domain:** `blife_packages`
- **Version:** 1.0.0
- **Minimum HA version:** 2024.1.0
- **Python:** 3.11+
- **IoT class:** `cloud_polling`

## Repository Structure

```
ha-blife/
├── CLAUDE.md                       # This file
├── README.md                       # User-facing documentation
├── Makefile                        # Deployment automation (SSH to HA host)
├── hacs.json                       # HACS (Home Assistant Community Store) metadata
├── .gitignore
└── custom_components/
    └── blife_packages/             # The integration
        ├── __init__.py             # Entry point: async_setup_entry / async_unload_entry
        ├── config_flow.py          # UI config flow + credential validation
        ├── const.py                # Constants (domain, API URL, sensor keys, attribute keys)
        ├── coordinator.py          # DataUpdateCoordinator: API calls, auth, data parsing
        ├── sensor.py               # Sensor entity definitions (CoordinatorEntity pattern)
        ├── manifest.json           # Integration metadata (domain, version, requirements)
        ├── strings.json            # Localization source strings
        ├── icon.png                # Integration icon
        └── translations/
            └── en.json             # English translations (mirrors strings.json)
```

All Python source lives under `custom_components/blife_packages/`. There is no separate `tests/` directory, `setup.py`, or `pyproject.toml` — this is a pure HA custom component, not a PyPI package.

## Architecture & Key Patterns

### Home Assistant Integration Lifecycle

1. **Config Flow** (`config_flow.py`): User provides username, password, and device_id via the HA UI. Credentials are validated against the BLife `/account/login` endpoint. On success, the token and user's first name are stored in the config entry data.

2. **Setup** (`__init__.py`): `async_setup_entry()` creates a `BLifePackagesCoordinator`, calls `async_config_entry_first_refresh()`, stores the coordinator in `hass.data[DOMAIN][entry.entry_id]`, and forwards setup to the `sensor` platform.

3. **Coordinator** (`coordinator.py`): Extends `DataUpdateCoordinator[BLifePackagesData]`. Fetches data every 5 minutes from `/my-deliveries/data-query/packages`. Handles token expiration by re-authenticating automatically. Returns `BLifePackagesData` containing a list of `Package` dataclass instances.

4. **Sensors** (`sensor.py`): Two sensors are created per config entry:
   - `{firstname}_packages_ready_to_collect` — count of uncollected packages (with package list as attributes)
   - `{firstname}_last_package_ref_number` — ref number of the most recent uncollected package

### Data Flow

```
BLife API  -->  BLifePackagesCoordinator._fetch_packages_data()
           -->  _parse_packages_response()  -->  BLifePackagesData
           -->  BLifePackagesSensor.native_value / extra_state_attributes
```

### Authentication

- Login endpoint: `POST {API_BASE_URL}/account/login`
- Token is returned in the `U-Set-Token` response header (not the body)
- Token is used as `Authorization: Bearer {token}` for subsequent requests
- Headers mimic the BLife mobile app (iPhone User-Agent, specific `App-Path`, `DeviceID`, etc.)
- On 401 during data fetch, coordinator re-authenticates once and retries
- Persistent auth failure triggers HA's reauth flow via `ConfigEntryAuthFailed`

### Data Models

- `Package` (dataclass): `package_id`, `ref_number`, `is_collection_required`, `latest_action`, `created_date`, `latest_action_date`, `addressed_to_unit`, `sender_name`, `courier_name`, `internal_number`
- `BLifePackagesData` (dataclass): `firstname`, `packages: list[Package]`, `last_updated`
- API timestamps are in milliseconds — converted via `datetime.fromtimestamp(ms / 1000)`

## Code Conventions

### Style

- **Type hints** throughout, using Python 3.11+ syntax (`X | None` instead of `Optional[X]`)
- **`from __future__ import annotations`** at the top of every module
- **`typing.Final`** for all constants in `const.py`
- **Dataclasses** for data models (not TypedDict or NamedTuple)
- **`_LOGGER = logging.getLogger(__name__)`** in every module
- **Docstrings** on all public classes and functions (short, imperative style)
- **No trailing commas** enforcement, but they are generally used in multi-line structures
- **Walrus operator** (`:=`) used in conditionals (e.g., `if unload_ok := ...`)

### Home Assistant Conventions

- Config entry data keys use `CONF_USERNAME`, `CONF_PASSWORD` from `homeassistant.const` and `CONF_DEVICE_ID` from local `const.py`
- Error classes (`InvalidAuth`, `CannotConnect`) extend `HomeAssistantError`
- Coordinator pattern: all API interaction is in the coordinator, sensors just read `self.coordinator.data`
- Entity unique IDs: `{device_id}_{sensor_key}`
- Device info groups entities under a single device per config entry
- `_attr_has_entity_name = True` — entity names are relative to the device

### Error Handling

- `ConfigEntryAuthFailed` — triggers HA reauth flow (persistent credential failure)
- `UpdateFailed` — logged by HA, coordinator retries on next interval
- `InvalidAuth` / `CannotConnect` — used in config flow to show UI errors
- `aiohttp.ClientError` — caught and wrapped in appropriate HA exceptions

## Development Workflow

### Deployment to Home Assistant

The Makefile provides deployment commands over SSH:

```bash
# Deploy files to HA instance (uses rsync, falls back to tar+ssh)
make deploy

# Restart Home Assistant after deployment
make restart

# Tail filtered logs (blife, ERROR, WARNING)
make logs

# Auto-deploy on file changes (requires fswatch)
make watch
```

Configure via environment variables:
```bash
export HA_HOST=homeassistant.local   # default
export HA_USER=root                  # default
export HA_CONFIG_PATH=/config        # default
```

### Adding a New Sensor

1. Add sensor key constant to `const.py`
2. Add a new `BLifePackagesSensorEntityDescription` entry in `sensor.py:get_sensor_descriptions()`
3. Define `value_fn` and optionally `extra_state_attributes_fn` lambdas/functions
4. Add translation keys to `strings.json` and `translations/en.json`

### Adding New API Data Fields

1. Add fields to the `Package` dataclass in `coordinator.py`
2. Update `Package.to_dict()` to include new fields
3. Update `_parse_packages_response()` to extract from API JSON
4. Expose via sensor attributes as needed

### Modifying Config Flow

1. Update `STEP_USER_DATA_SCHEMA` in `config_flow.py` for new fields
2. Update `validate_input()` if new fields affect validation
3. Update `strings.json` and `translations/en.json` for UI labels
4. Ensure `strings.json` and `translations/en.json` stay in sync

## Dependencies

- **Runtime:** `aiohttp>=3.8.0` (declared in `manifest.json`)
- **Implicit (from HA):** `voluptuous`, `homeassistant` core libraries
- **No test dependencies** currently configured

## Important Files Reference

| File | Purpose |
|------|---------|
| `const.py` | All constants: domain, API URL, scan interval, sensor keys, attribute keys |
| `coordinator.py` | All BLife API interaction, authentication, and data parsing |
| `config_flow.py` | UI setup flow, credential validation, reauth handling |
| `sensor.py` | Sensor entity definitions and state computation |
| `manifest.json` | Integration metadata (version, requirements, iot_class) |
| `strings.json` | Source localization strings (must sync with `translations/en.json`) |

## Things to Watch Out For

- **Token in response header:** The BLife API returns the auth token in the `U-Set-Token` HTTP header, not in the JSON body. This is unusual and easy to miss.
- **Timestamps in milliseconds:** API date fields use epoch milliseconds, not seconds.
- **Header mimicry:** API requests must include mobile-app-like headers (`User-Agent`, `App-Path`, `DeviceID`, etc.) or the API may reject them.
- **`strings.json` and `translations/en.json` must stay in sync** — they have identical structure and content.
- **No test suite exists** — changes should be manually tested against a running HA instance.
- **Sensitive data** (credentials, tokens) is never stored in the repository — only in HA's config entry system. Files like `deploy.local.sh` and `.env` are gitignored.
