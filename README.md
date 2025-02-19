# Tibber Pricing DE Sensor for Home Assistant

Get Tibber dynamic pricing information in home-assistant (Germany only, no account needed)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![Sponsor][sponsor-shield]][sponsor]

## Installation

### HACS - Recommended

- Have [HACS](https://hacs.xyz) installed, this will allow you to easily manage and track updates.
- Goto the Custom Repository menu in HACS, paste https://github.com/cyberjunky/home-assistant-tibber_pricing_de as URL and select Integration as type.
- Search for 'Tibber Pricing DE' in HACS.
- Click the Download button at the bottom of the page of the found integration.
- Restart Home Assistant.
- Under Services -> Devices & services click the Add Integration button, search for 'Tibber Pricing DE'.
- Configure the integration using the instructions below.

### Manual - Without HACS

- Copy directory `custom_components/tibber_pricing_de` to your `<config dir>/custom_components` directory.
- Restart Home-Assistant.
- Add the integration and configure it using the instructions below

## Configuration Flow

This component supports a configuration flow that allows you to set up the sensor through the Home Assistant UI. You will be prompted to enter the name and postal code during the setup process.

## Usage

Once configured, the sensor will provide the following data:

- Current Price
- Next Hour Price
- Highest Price Today
- Lowest Price Today
- Timestamps for the highest and lowest prices today

You can view these values in the Home Assistant dashboard.

## Charts

Install apexcharts via HACS.
You can define this chart to get the today price per hour.
```
views:
  - title: Home
    cards:
      - type: custom:apexcharts-card
        graph_span: 24h
        span:
          start: day
          offset: '-1h'
        now:
          show: true
          label: Now
        header:
          show: true
          title: Stroomprijs vandaag (€/kWh)
        series:
          - entity: sensor.your_sensor_current_price
            stroke_width: 2
            float_precision: 4
            type: column
            opacity: 1
            color: ''
            data_generator: |
              return entity.attributes.prices.map((record, index) => {
                return [record.timestamp, record.price];
              });
        yaxis:
          - id: Prijs
            decimals: 4
```
<img width="377" alt="image" src="https://github.com/user-attachments/assets/ca7b8bc7-b9f3-4bb0-aabb-55017e562337" />

## Debugging

Add the relevant lines below to the `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tibber_pricing_de: debug
```

Or click Debug button on the integration page inside Home Assistant

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
