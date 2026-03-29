# TinyTuya Light

A Home Assistant custom integration for controlling Tuya-based lights locally via [tinytuya](https://github.com/jasonacox/tinytuya). Designed for devices running Tuya protocol 3.4/3.5 that aren't supported by other local Tuya integrations.

## Features

- Local control (no cloud dependency)
- Tuya protocol 3.1 through 3.5 support
- Brightness and color temperature control
- Automatic reconnection on failure

## Installation

### Manual

Copy the `tinytuya_light` folder to your Home Assistant `custom_components` directory.

### HACS

Add this repository as a custom repository in HACS:

1. HACS > Integrations > 3-dot menu > Custom repositories
2. Add `https://github.com/torbjvi/tinytuya_light` as an Integration
3. Download and restart Home Assistant

## Configuration

Add to your `configuration.yaml`:

```yaml
light:
  - platform: tinytuya_light
    name: "My Light"
    device_id: "your_device_id"
    host: "192.168.1.100"
    local_key: "your_local_key"
    protocol_version: 3.5
```

### Options

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `name` | No | `TinyTuya Light` | Friendly name |
| `device_id` | Yes | | Tuya device ID |
| `host` | Yes | | Device IP address |
| `local_key` | Yes | | Device local key |
| `protocol_version` | No | `3.5` | Tuya protocol version |
| `min_kelvin` | No | `2700` | Minimum color temperature in Kelvin |
| `max_kelvin` | No | `6500` | Maximum color temperature in Kelvin |

## Getting device credentials

Use [tinytuya](https://github.com/jasonacox/tinytuya) to scan your network and retrieve device IDs and local keys:

```bash
pip install tinytuya
python -m tinytuya scan
```

Or retrieve keys from the [Tuya IoT Platform](https://iot.tuya.com).
