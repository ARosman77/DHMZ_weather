# DHMZ Weather

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

_Integration to integrate with [DHMZ_weather][DHMZ_weather]._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from DHMZ provided XML data.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `DHMZ_weather`.
1. Download _all_ the files from the `custom_components/DHMZ_weather/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "DHMZ Weather"

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[DHMZ_weather]: https://github.com/ARosman77/DHMZ_weather
[commits-shield]: https://img.shields.io/github/commit-activity/y/ARosman77/DHMZ_weather.svg?style=for-the-badge
[commits]: https://github.com/ARosman77/DHMZ_weather/commits/main
[exampleimg]: example.png
[license-shield]: https://img.shields.io/github/license/ARosman77/DHMZ_weather.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-ARosman77%20-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ARosman77/DHMZ_weather.svg?style=for-the-badge
[releases]: https://github.com/ARosman77/DHMZ_weather/releases
