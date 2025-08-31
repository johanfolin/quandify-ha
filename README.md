# quandify-ha
An attempt to create a Home Assistant integration for Quandify's API

# Quandify Home Assistant Integration

[![hacs][hacsbadge]][hacs]
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]

Monitor your Quandify water consumption directly in Home Assistant's Energy dashboard.

## Installation

### HACS (Recommended)

1. In HACS, go to "Integrations"
2. Click the "+" button
3. Search for "Quandify"
4. Install the integration
5. Restart Home Assistant
6. Add the integration in Settings → Devices & Services

### Manual Installation

1. Download this repository
2. Copy `custom_components/quandify` to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Add the integration in Settings → Devices & Services

## Configuration

You'll need your Quandify credentials:
Create API account at https://partner.quandify.com.
Use GUID and password for the user. Organization ID is account owner's GUID.

- **Account ID**: Your GUID account identifier
- **Password**: Your Quandify account password  
- **Organization ID**: Your organization GUID

## Features

- ✅ Energy Dashboard integration
- ✅ Automatic authentication handling
- ✅ Hourly data updates
- ✅ Daily consumption tracking

## Support

For issues or feature requests, please [open an issue](https://github.com/johanfolin/quandify-ha/issues).

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[releases-shield]: https://img.shields.io/github/release/johanfolin/quandify-ha.svg
[releases]: https://github.com/johanfolin/quandify-ha/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/johanfolin/quandify-ha.svg
[commits]: https://github.com/johanfolin/quandify-ha/commits/main
