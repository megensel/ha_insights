"""Constants for the HA Insights integration."""

# Integration domain
DOMAIN = "ha_insights"
DEFAULT_NAME = "HA Insights"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = "ha_insights_data"

# Configuration
CONF_SCAN_INTERVAL = "scan_interval"
CONF_EXCLUDED_ENTITIES = "excluded_entities"
CONF_TRACKED_DOMAINS = "tracked_domains"
CONF_MIN_STATE_CHANGES = "min_state_changes"
CONF_MAX_SUGGESTIONS = "max_suggestions"
CONF_PURGE_DAYS = "purge_days"

# Default values
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_MIN_STATE_CHANGES = 50  # minimum state changes to detect patterns
DEFAULT_MAX_SUGGESTIONS = 15  # maximum suggestions to show
DEFAULT_PURGE_DAYS = 30  # days to keep insights before purging
DEFAULT_INSIGHTS_SCAN_INTERVAL = 240  # minutes between insights generation
DEFAULT_AGGREGATION_WINDOW = 10  # minutes between state aggregation

# Commonly tracked domains for home automation
DEFAULT_TRACKED_DOMAINS = [
    "light",
    "switch",
    "climate",
    "sensor",
    "binary_sensor",
    "cover",
    "media_player",
    "person",
    "device_tracker",
    "automation",
    "scene",
    "script",
]

# All available domains that could be tracked
AVAILABLE_DOMAINS = [
    "light",
    "switch",
    "climate",
    "sensor",
    "binary_sensor",
    "cover",
    "media_player",
    "camera",
    "fan",
    "person",
    "device_tracker",
    "automation",
    "scene",
    "script",
    "vacuum",
    "water_heater",
    "lock",
    "alarm_control_panel",
    "weather",
    "sun",
    "input_boolean",
    "input_number",
    "input_select",
    "input_text",
    "input_datetime",
    "humidifier",
    "update",
    "remote",
    "button",
]

# Events
EVENT_NEW_INSIGHT = "ha_insights_new_insight"

# Dispatcher signals
SIGNAL_INSIGHTS_UPDATED = "ha_insights_insights_updated"

# Insight types
INSIGHT_TYPE_AUTOMATION = "automation"
INSIGHT_TYPE_ENERGY = "energy"
INSIGHT_TYPE_COMFORT = "comfort"
INSIGHT_TYPE_CONVENIENCE = "convenience"
INSIGHT_TYPE_SECURITY = "security"

# Entity platforms
PLATFORMS = ["sensor"]

# Sensor
SENSOR_INSIGHT = "insight"
SENSOR_INSIGHT_SUMMARY = "insight_summary"

# Icons by insight type
ICON_AUTOMATION = "mdi:robot"
ICON_ENERGY = "mdi:lightning-bolt"
ICON_COMFORT = "mdi:thermometer"
ICON_CONVENIENCE = "mdi:gesture-tap-button"
ICON_SECURITY = "mdi:shield-home"
ICON_SUMMARY = "mdi:lightbulb-group"

# Limits
MAX_STATE_CHANGES = 1000  # Maximum state changes to keep in history 