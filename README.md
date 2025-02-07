# Tibber Pricing DE

Get Tibber dynamic pricing information in home-assistant (Germany only, no account needed)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![Sponsor][sponsor-shield]][sponsor]

**This integration will set up the following platforms.**

| Platform | Description                                                    |
| -------- | -------------------------------------------------------------- |


## Installation

### HACS - Recommended

- Have [HACS](https://hacs.xyz) installed, this will allow you to easily manage and track updates.
- Search for 'Tibber Pricing DE'.
- Click Install below the found integration.
- Configure using the configuration instructions below.
- Restart Home-Assistant.

### Manual

- Copy directory `custom_components/tibber_pricing_de` to your `<config dir>/custom_components` directory.
- Configure with config below.
- Restart Home-Assistant.

## Configuration

Edit configuration.yaml and enter something like this.
```
sensor:
  - platform: tibber_pricing_de
    name: Hartmannsdorf
    postalcode: 07586
```
Restart Home Assistant,

## Debugging

Add the relevant lines below to the `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tibber_pricing_de: debug
```

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[tibber_pricing_de]: https://github.com/cyberjunky/home-assistant-tibber_pricing_de
[commits-shield]: https://img.shields.io/github/commit-activity/y/cyberjunky/home-assistant-tibber_pricing_de.svg?style=for-the-badge
[commits]: https://github.com/cyberjunky/home-assistant-tibber_pricing_de/commits/main
[license-shield]: https://img.shields.io/github/license/cyberjunky/home-assistant-tibber_pricing_de.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40cyberjunky-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/cyberjunky/home-assistant-tibber_pricing_de.svg?style=for-the-badge
[releases]: https://github.com/cyberjunky/home-assistant-tibber_pricing_de/releases
[sponsor-shield]: https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86
[sponsor]: https://github.com/sponsors/cyberjunky
