# HA Insights

Home Assistant integration for pattern analysis and actionable insights to improve your smart home.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/GITHUB_USERNAME/ha_insights.svg)](https://github.com/GITHUB_USERNAME/ha_insights/releases)

## Overview

HA Insights continuously analyzes your Home Assistant environment to identify usage patterns, correlations between entities, and optimization opportunities. The integration provides actionable suggestions for:

- **Automations**: Time-based patterns and entity correlations
- **Energy savings**: Identify high usage periods and optimization opportunities
- **Comfort improvements**: Temperature and climate optimization
- **Convenience**: Make your smart home even more helpful
- **Security**: Identify potential security improvements

## Features

- 🔍 **Pattern Detection**: Identifies daily and weekly patterns in entity usage
- 🔄 **Entity Correlation**: Discovers relationships between sensors and controllable devices
- 💡 **Actionable Suggestions**: Generates ready-to-use automation YAML
- 📊 **Insights Dashboard**: All insights accessible as Home Assistant sensors
- ⚙️ **Customizable**: Configure tracked domains, analysis frequency, and more

## Installation

### HACS Installation (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository to HACS as a custom repository:
   - Open HACS in Home Assistant
   - Click on "Integrations"
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL: `https://github.com/GITHUB_USERNAME/ha_insights`
   - Category: Integration
3. Search for "HA Insights" in HACS and install
4. Restart Home Assistant
5. Add the integration in Settings -> Devices & Services -> Add Integration

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/GITHUB_USERNAME/ha_insights/releases)
2. Extract the `ha_insights` directory to your `custom_components` directory
3. Restart Home Assistant
4. Add the integration in Settings -> Devices & Services -> Add Integration

## Configuration

HA Insights offers several configuration options:

- **Analysis Interval**: How often to analyze patterns (default: 60 minutes)
- **Tracked Domains**: Which entity domains to monitor (default: common domains like light, switch, climate, etc.)
- **Excluded Entities**: Specific entities to exclude from analysis
- **Minimum State Changes**: Threshold for pattern detection (default: 50 changes)
- **Maximum Suggestions**: Limit the number of suggestions (default: 15)
- **Purge Days**: How long to keep insights before purging (default: 30 days)

## Using Insights

Once installed, HA Insights will begin monitoring your Home Assistant instance and generate insights as it detects patterns.

### Viewing Insights

Insights are available through several methods:

1. **Sensors**: Each insight is exposed as a sensor entity with detailed attributes
2. **Summary Sensor**: A summary sensor provides an overview of all insights
3. **Lovelace Cards**: You can create cards to display insights (examples below)

### Available Services

HA Insights provides the following services:

- `ha_insights.generate_insights`: Manually trigger insight generation
- `ha_insights.dismiss_insight`: Mark an insight as dismissed
- `ha_insights.mark_implemented`: Mark an insight as implemented

### Example Lovelace UI

Here's a simple example of a Lovelace card to display insights:

```yaml
type: entities
title: HA Insights
entities:
  - entity: sensor.insights_summary
  - type: divider
  - type: custom:auto-entities
    card:
      type: entities
      title: Automation Suggestions
    filter:
      include:
        - entity_id: sensor.insight_*
          attributes:
            type: automation
      exclude:
        - attributes:
          dismissed: true
```

For more advanced UI examples, see [example_lovelace.yaml](ha_insights/example_lovelace.yaml) in this repository.

## FAQ

**Q: How long before I start seeing insights?**
A: HA Insights needs to collect enough data to identify patterns. Typically, you'll start seeing basic insights after 1-2 days of usage, with more sophisticated patterns emerging after a week or more.

**Q: Does this affect Home Assistant performance?**
A: HA Insights is designed to be lightweight and runs analysis periodically rather than continuously. It should have minimal impact on performance.

**Q: Can I suggest features or report bugs?**
A: Yes! Please use the [GitHub issue tracker](https://github.com/GITHUB_USERNAME/ha_insights/issues) for feature requests and bug reports.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 