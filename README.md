# BLife Concierge Packages

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/Stormsys/ha-blife?style=for-the-badge)](https://github.com/Stormsys/ha-blife/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

[![Validate with hassfest](https://github.com/Stormsys/ha-blife/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/Stormsys/ha-blife/actions/workflows/hassfest.yaml)
[![HACS Validation](https://github.com/Stormsys/ha-blife/actions/workflows/validate.yaml/badge.svg)](https://github.com/Stormsys/ha-blife/actions/workflows/validate.yaml)

---

A custom [Home Assistant](https://www.home-assistant.io/) integration for **[Ballymore Life (BLife)](https://www.ballymorelife.com/)** residents. Track your concierge parcels and packages directly from your smart home dashboard — never miss a delivery again.

> **Alpha Release** — This integration is in early development. Expect breaking changes between versions. Please [report issues](https://github.com/Stormsys/ha-blife/issues) if you encounter any problems.

## What it does

This integration connects to the BLife concierge system used in Ballymore residential developments and creates sensors that show:

| Sensor | Description |
|--------|-------------|
| **Packages Ready to Collect** | Count of parcels waiting at the concierge desk, with full details in attributes |
| **Last Package Reference** | Reference number of your most recent uncollected parcel for quick pickup |

Sensors update automatically every 5 minutes, and the integration handles token refresh and re-authentication seamlessly.

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant instance
2. Click **Integrations** > three-dot menu > **Custom repositories**
3. Add `https://github.com/Stormsys/ha-blife` with category **Integration**
4. Search for **BLife Concierge Packages** and install it
5. Restart Home Assistant

### Manual

1. Download the [latest release](https://github.com/Stormsys/ha-blife/releases)
2. Copy the `custom_components/blife_packages` folder into your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for **BLife Concierge Packages**
4. Enter your credentials:

| Field | Description |
|-------|-------------|
| **Username** | Your BLife account email |
| **Password** | Your BLife account password |
| **Device ID** | Your building's unique device identifier (from the BLife app) |

> **Finding your Device ID:** Open the BLife mobile app, go to Settings/About, and locate your device identifier. Alternatively, inspect the app's network traffic to find the `DeviceID` header value.

## Sensors

After setup, the integration creates a device called **BLife Concierge** with two sensors:

### Packages Ready to Collect
- **State:** Number of parcels waiting for pickup
- **Attributes:**
  - `packages` — List of uncollected parcels, each containing:
    - `ref_number` — Reference code for the concierge
    - `sender_name` — Who sent the parcel
    - `courier_name` — Delivery carrier
    - `created_date` — When the parcel arrived
    - `latest_action` — Current status
    - `addressed_to_unit` — Your unit number

### Last Package Reference
- **State:** Reference number of the most recently arrived uncollected parcel
- **Attributes:**
  - `last_package` — Full details of the most recent parcel

## Example Automations

### Notify when a new parcel arrives

```yaml
automation:
  - alias: "New Parcel at Concierge"
    triggers:
      - trigger: state
        entity_id: sensor.blife_concierge_packages_ready_to_collect
    conditions:
      - condition: template
        value_template: >
          {{ trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "New Parcel"
          message: >
            You have {{ states('sensor.blife_concierge_packages_ready_to_collect') }}
            parcel(s) waiting at the concierge.
```

### Evening reminder if parcels are uncollected

```yaml
automation:
  - alias: "Parcel Pickup Reminder"
    triggers:
      - trigger: time
        at: "18:00:00"
    conditions:
      - condition: numeric_state
        entity_id: sensor.blife_concierge_packages_ready_to_collect
        above: 0
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "Parcel Reminder"
          message: >
            You still have
            {{ states('sensor.blife_concierge_packages_ready_to_collect') }}
            parcel(s) to collect from the concierge.
```

### Display on a dashboard card

```yaml
type: entities
title: Concierge Parcels
entities:
  - entity: sensor.blife_concierge_packages_ready_to_collect
    name: Waiting for Pickup
  - entity: sensor.blife_concierge_last_package_ref_number
    name: Latest Ref Number
```

## Requirements

- Home Assistant **2024.1.0** or later
- A **Ballymore Life (BLife)** resident account
- Your building's **Device ID**

## Contributing

Contributions are welcome! Please open an [issue](https://github.com/Stormsys/ha-blife/issues) first to discuss what you'd like to change.

## License

[MIT](LICENSE)
