# HASGP

A Home Assistant custom integration that fetches the latest Singapore electricity tariff from [data.gov.sg](https://data.gov.sg) and creates corresponding sensors.

## Features

### Device Energy Cost

- Automatically pulls electricity tariff data from data.gov.sg every 24 hours
- Uses a GST-inclusive tariff for cost calculation
- Creates cost sensors from selected entities with device class `energy`
- Allows custom names for generated cost sensors
- Falls back to the previous month if the current month's tariff is not yet available

### Weather
- Coming soon

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hasgp&repository=hasgp&category=integration)

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=hasgp)

## License

### Project

Licensed under the [MIT License](LICENSE).

### Dataset

Sourced from [data.gov.sg](https://data.gov.sg). Usage is governed by the [Singapore Open Data Licence](https://data.gov.sg/open-data-licence).