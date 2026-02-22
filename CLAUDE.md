# CLAUDE.md

## Project Overview

**BLife Concierge Packages** is a Home Assistant custom integration that tracks parcels at a building's concierge desk via the Ballymore Life API. It polls the API every 5 minutes and exposes sensor entities showing package counts and details.

- **Domain:** `blife_packages`
- **Version:** 0.1.0 (Alpha)
- **Minimum HA version:** 2024.1.0
- **Python:** 3.11+
- **IoT class:** `cloud_polling`
- **HACS:** Custom repository

## Repository Structure

```
ha-blife/
├── CLAUDE.md                           # This file
├── README.md                           # User-facing documentation
├── Makefile                            # Deployment automation (SSH to HA host)
├── hacs.json                           # HACS metadata
├── .github/
│   └── workflows/
│       ├── hassfest.yaml               # HA manifest validation CI
│       └── validate.yaml               # HACS validation CI
└── custom_components/
    └── blife_packages/                 # The integration
        ├── __init__.py                 # Entry point: async_setup_entry / async_unload_entry
        ├── api.py                      # Shared API helpers (headers, payloads, URLs)
        ├── config_flow.py              # UI config flow + credential validation
        ├── const.py                    # Constants (domain, API URL, sensor keys)
        ├── coordinator.py              # DataUpdateCoordinator: API calls, auth, data parsing
        ├── sensor.py                   # Sensor entity definitions (CoordinatorEntity pattern)
        ├── manifest.json               # Integration metadata (domain, version)
        ├── strings.json                # Localization source strings
        ├── icon.png                    # Integration icon
        └── translations/
            └── en.json                 # English translations (must mirror strings.json)
```

## Architecture

### Module Responsibilities

| Module | Role |
|--------|------|
| `api.py` | Shared HTTP header builders, login payload builder, URL constants |
| `config_flow.py` | UI config flow, credential validation, reauth handling |
| `coordinator.py` | `DataUpdateCoordinator` subclass — all API interaction, auth token management, response parsing |
| `sensor.py` | Sensor entity definitions — reads from coordinator data, no API calls |
| `const.py` | Domain, config keys, scan interval, sensor key constants |
| `__init__.py` | Integration lifecycle: setup, unload |

### Data Flow

```
BLife API  →  coordinator._fetch_packages_data()
           →  coordinator._parse_packages_response()  →  BLifePackagesData
           →  BLifePackagesSensor.native_value / extra_state_attributes
```

### Authentication

- Login: `POST /account/login` — token returned in `U-Set-Token` response header
- Data: `Authorization: Bearer {token}` header on subsequent requests
- Headers mimic the BLife mobile app (iPhone UA, `App-Path`, `DeviceID`, etc.)
- On 401 during data fetch, coordinator re-authenticates once and retries
- Persistent auth failure triggers HA's reauth flow via `ConfigEntryAuthFailed`

### HTTP Sessions

The integration uses Home Assistant's shared `aiohttp.ClientSession` via `async_get_clientsession(hass)`. Never create standalone `aiohttp.ClientSession` instances.

### Data Models

- **`Package`** (dataclass): `package_id`, `ref_number`, `is_collection_required`, `latest_action`, `created_date`, `latest_action_date`, `addressed_to_unit`, `sender_name`, `courier_name`, `internal_number`
- **`BLifePackagesData`** (dataclass): `firstname`, `packages: list[Package]`, `last_updated`
  - `.uncollected_packages` — filtered list of packages not yet collected
  - `.packages_ready_to_collect` — count of uncollected
- All timestamps are **UTC-aware** (`datetime.fromtimestamp(ms / 1000, tz=timezone.utc)`)

### Sensors

Two sensors per config entry, defined as static `SENSOR_DESCRIPTIONS` list:

| Sensor Key | Translation Key | State | Attributes |
|------------|----------------|-------|------------|
| `packages_ready_to_collect` | `packages_ready_to_collect` | Count (int) | `packages`: list of uncollected parcels |
| `last_package_ref_number` | `last_package_ref_number` | Ref string or None | `last_package`: most recent parcel dict |

Entity naming uses `_attr_has_entity_name = True` with `translation_key` only — do **not** set `name` on entity descriptions.

## Code Conventions

### Style

- `from __future__ import annotations` at the top of every module
- Type hints using Python 3.11+ syntax (`X | None`, not `Optional[X]`)
- `typing.Final` for all constants
- Dataclasses for data models
- `_LOGGER = logging.getLogger(__name__)` in every module
- Private attributes for sensitive data (`self._username`, `self._password`, `self._token`)
- Walrus operator (`:=`) used in conditionals

### Home Assistant Patterns

- Use `CONF_USERNAME` / `CONF_PASSWORD` from `homeassistant.const` (not local redefinitions)
- Use `ConfigEntryAuthFailed` from `homeassistant.exceptions`
- Use `async_get_clientsession(hass)` — never create manual `aiohttp.ClientSession`
- `requirements` in `manifest.json` must be empty — `aiohttp` is a HA core dep
- Sensor descriptions are a module-level constant list, not generated per-entry
- `available` property checks both `last_update_success` and `data is not None`
- `native_value` and `extra_state_attributes` guard against `coordinator.data is None`

### Error Handling

- `ConfigEntryAuthFailed` — triggers HA reauth flow
- `UpdateFailed` — coordinator retries on next interval
- `InvalidAuth` / `CannotConnect` — config flow UI errors
- JSON parse errors caught with `aiohttp.ContentTypeError` / `ValueError`
- API response type-checked (`isinstance(data, dict)`)
- Null-safe nested dict access: `(result.get("key") or {}).get("nested")`

## Development Workflow

### Deployment to HA

```bash
make deploy              # rsync files to HA instance over SSH
make restart             # restart HA core
make logs                # tail filtered logs
make watch               # auto-deploy on file changes (requires fswatch)
```

Configure via env vars: `HA_HOST`, `HA_USER`, `HA_CONFIG_PATH`.

### CI/CD

Two GitHub Actions workflows run on push/PR:
- **hassfest** — validates `manifest.json` against HA requirements
- **HACS Validation** — validates HACS repository structure

### Common Changes

**Adding a new sensor:**
1. Add sensor key constant to `const.py`
2. Add a `BLifePackagesSensorEntityDescription` to `SENSOR_DESCRIPTIONS` in `sensor.py`
3. Define `value_fn` and optionally `extra_state_attributes_fn`
4. Add translation key to both `strings.json` and `translations/en.json`

**Adding new API data fields:**
1. Add fields to the `Package` dataclass in `coordinator.py`
2. Update `Package.to_dict()`
3. Update `_parse_packages_response()` to extract from API JSON
4. Expose via sensor attributes as needed

**Modifying API headers/payload:**
1. Edit the relevant builder function in `api.py` — changes propagate to both config flow and coordinator

**Modifying config flow:**
1. Update `STEP_USER_DATA_SCHEMA` in `config_flow.py`
2. Update `validate_input()` if new fields affect validation
3. Keep `strings.json` and `translations/en.json` in sync

## Important Gotchas

- **Token in response header:** Auth token comes back in the `U-Set-Token` HTTP header, not the JSON body
- **Timestamps in milliseconds:** API date fields use epoch milliseconds, not seconds
- **Header mimicry:** API requests need mobile-app-like headers or the API rejects them
- **`strings.json` and `translations/en.json` must stay in sync** — identical structure
- **No test suite** — changes should be manually tested against a running HA instance
- **`requirements` must be empty** — `aiohttp` is provided by HA core; listing it causes pip conflicts
- **Entity names:** Use `translation_key` only, never set `name` alongside `_attr_has_entity_name = True`
- **Sensitive data:** Credentials are stored in HA's config entry system only. `deploy.local.sh` and `.env` are gitignored
