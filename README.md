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
- Under Settings -> Devices & services click the Add Integration button, search for 'Tibber Pricing DE'.
- Configure the integration using the instructions below.

### Manual - Without HACS

- Copy directory `custom_components/tibber_pricing_de` to your `<config dir>/custom_components` directory.
- Restart Home-Assistant.
- Add the integration and configure it using the instructions below

## Configuration

Add the integration from **Settings -> Devices & services** and enter your five-digit German postal code. The postal code is validated against the Tibber API; each postal code can be added once.

## Sensors

Prices are in EUR/kWh including VAT, taxes and grid fees for your postal code. Each entry creates a service device with these sensors:

| Sensor | State |
|---|---|
| Current price | Price for the current hour |
| Next hour price | Price for the next hour (after 23:00 this needs tomorrow's prices, published around 13:00) |
| Highest price today | Highest hourly price today |
| Highest price today hour | Start of the most expensive hour today (timestamp) |
| Lowest price today | Lowest hourly price today |
| Lowest price today hour | Start of the cheapest hour today (timestamp) |

Every sensor has a `price_components` attribute with the breakdown (power, taxes, grid) for the hour it refers to.
The current price sensor also has:

- `prices`: today's hourly prices as `{timestamp, price}`, with ISO 8601 timestamps in local time
- `prices_tomorrow`: the same for tomorrow, empty until Tibber publishes them
- `today`: Tibber's average price for today
- `monthly`: the monthly fees

The data is polled once an hour, and the states move on at every full hour.

## Charts

Install apexcharts via HACS.
You can define this chart to get today's price per hour.
```
views:
  - title: Home
    cards:
      - type: custom:apexcharts-card
        graph_span: 24h
        span:
          start: day
        now:
          show: true
          label: Now
        header:
          show: true
          title: Strompreis heute (EUR/kWh)
        series:
          - entity: sensor.tibber_pricing_de_10115_current_price
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
          - id: Preis
            decimals: 4
```
<img width="374" alt="image" src="https://github.com/user-attachments/assets/1fb98c13-0751-4fe6-b977-93b9e79c2fb0" />


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
