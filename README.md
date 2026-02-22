# BLife Concierge Packages - Home Assistant Integration

A custom Home Assistant integration for tracking packages at your building's concierge desk.

## Features

- **Configuration UI**: Easy setup through Home Assistant's UI with username, password, and device ID
- **Async-first**: Built with modern async patterns using DataUpdateCoordinator
- **Package Count Sensor**: `{firstname}_packages_ready_to_collect` - Shows count of packages waiting for pickup
- **Package List Sensor**: `{firstname}_packages_list` - Full list of all packages with codes and details
- **Auto-refresh**: Polls for updates every 5 minutes (configurable)
- **Reauth Support**: Handles credential expiration gracefully

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Click on "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Install "BLife Concierge Packages"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/blife_packages` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Secrets – what not to commit

- **BLife credentials** (username, password, device ID) are only entered in Home Assistant’s UI and stored in HA’s config – they are never in this repo.
- **Deploy script**: Do not hardcode your Home Assistant host or SSH user. Use environment variables:
  - `export HA_HOST=192.168.0.117` (or `homeassistant.local`)
  - `export HA_USER=root`
  - `export HA_CONFIG_PATH=/config`
  - Then run `./deploy.sh`
- Optional: create a `deploy.local.sh` that sets these and run that instead; `deploy.local.sh` is in `.gitignore` and will not be committed.

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "BLife Concierge Packages"
4. Enter your credentials:
   - **Username**: Your BLife account email/username
   - **Password**: Your BLife account password
   - **Device ID**: Your building's unique device identifier

## Sensors

After configuration, the integration creates the following sensors:

### Packages Ready to Collect
- **Entity ID**: `sensor.{firstname}_packages_ready_to_collect`
- **State**: Number of packages ready for pickup
- **Attributes**:
  - `packages`: List of ready packages with details

### Packages List
- **Entity ID**: `sensor.{firstname}_packages_list`
- **State**: Total number of packages
- **Attributes**:
  - `packages`: Full list of all packages
  - `ready_count`: Number ready for pickup
  - `collected_count`: Number already collected

## Package Attributes

Each package in the list includes:
- `package_id`: Unique package identifier
- `code`: Pickup code for the concierge
- `description`: Package description
- `arrived_at`: Arrival timestamp
- `status`: Current status (ready/collected)
- `sender`: Package sender
- `carrier`: Delivery carrier

## Example Automations

### Notify when new package arrives

```yaml
automation:
  - alias: "New Package Notification"
    trigger:
      - platform: state
        entity_id: sensor.john_packages_ready_to_collect
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
    action:
      - service: notify.mobile_app
        data:
          title: "📦 New Package!"
          message: "You have {{ states('sensor.john_packages_ready_to_collect') }} package(s) ready for pickup"
```

### Daily package summary

```yaml
automation:
  - alias: "Daily Package Summary"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.john_packages_ready_to_collect
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "📬 Package Reminder"
          message: "Don't forget! You have {{ states('sensor.john_packages_ready_to_collect') }} package(s) waiting at the concierge."
```

## API Integration

The integration currently uses stub data for development. To connect to your actual BLife API:

1. Update `coordinator.py`:
   - Replace the stub `_fetch_packages_data()` method with actual API calls
   - Implement proper authentication flow

2. Update `config_flow.py`:
   - Replace the stub `validate_input()` function with actual API validation

3. Update `const.py`:
   - Set `API_BASE_URL` to your actual API endpoint

## Development

### File Structure

```
custom_components/blife_packages/
├── __init__.py          # Integration setup
├── config_flow.py       # Configuration UI flow
├── const.py             # Constants and configuration
├── coordinator.py       # Data update coordinator
├── manifest.json        # Integration metadata
├── sensor.py            # Sensor entities
├── strings.json         # Translation strings
└── translations/
    └── en.json          # English translations
```

### Requirements

- Home Assistant 2024.1.0 or later
- Python 3.11+

## License

MIT License

