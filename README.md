# Etelecom Integration for Home Assistant

Version: `0.0.1`

![GitHub Release](https://img.shields.io/github/v/release/OddanN/etelecom_for_home_assistant?style=flat-square)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/OddanN/etelecom_for_home_assistant?style=flat-square)
![GitHub Downloads](https://img.shields.io/github/downloads/OddanN/etelecom_for_home_assistant/total?style=flat-square)
![License](https://img.shields.io/github/license/OddanN/etelecom_for_home_assistant?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

<p align="center">
  <img src="logo.png" alt="EIRC SPB logo" width="200">
</p>

The Etelecom Integration allows you to connect your Home Assistant instance to the Etelecom (AT-HOME / info-lan.ru)
personal account API and create sensors with the main contract and balance information.

## Installation

Installation is easiest via the [Home Assistant Community Store
(HACS)](https://hacs.xyz/), which is the best place to get third-party
integrations for Home Assistant. Once you have HACS set up, simply click the button below (requires My Home Assistant
configured) or
follow the [instructions for adding a custom
repository](https://hacs.xyz/docs/faq/custom_repositories) and then
the integration will be available to install like any other.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=OddanN&repository=etelecom_for_home_assistant&category=integration)

## Configuration

After installing, configure the integration using the Integrations UI. No manual YAML configuration is required.
Go to Settings / Devices & Services and press the Add Integration button, or click the shortcut button below (requires
My Home Assistant configured).

[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg?style=flat-square)](https://my.home-assistant.io/redirect/config_flow_start/?domain=etelecom_for_home_assistant)

### Setup

- Enter your Etelecom login.
- Enter your Etelecom password.
- Finish setup. The integration will authenticate and create entities for the account.

### Integration Options

- Update Interval: Set the polling interval in hours. Default is 12 hours, minimum is 1 hour, maximum is 24 hours.

## Entities

The integration creates a device for the personal account and the following sensors:

- Account ID: Contract account number.
- Bonus Balance: Bonus balance from the loyalty program.
- Customer Name: Contract owner name.
- Cash Balance: Monetary balance in RUB.
- Contract Address: Service address.
- Next Charge Date: Date of the next planned charge.
- Next Charge Amount: Planned charge amount in RUB.

## Notes

- This integration requires an active Etelecom account.
- Data is fetched from `https://api.billing.at-home.ru/app/index.php`.
- Authentication uses the same login and password as the customer portal.
- For support or to report issues, open an issue on the
  [GitHub repository](https://github.com/OddanN/etelecom_for_home_assistant/issues).

## Debug

For DEBUG add to `configuration.yaml`

```yaml
logger:
  default: info
  logs:
    custom_components.etelecom_for_home_assistant: debug
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
