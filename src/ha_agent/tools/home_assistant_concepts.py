"""
Home Assistant Concepts and Terminology Guide.

This module provides detailed information about Home Assistant concepts and API
structure to help agents better understand how to interact with Home Assistant.
"""

# Entity Domains and Types
DOMAINS = {
    "light": {
        "description": "Lighting devices that can be turned on/off and often have brightness, color controls",
        "common_services": ["turn_on", "turn_off", "toggle"],
        "attributes": ["brightness", "rgb_color", "color_temp", "effect", "supported_features"],
        "states": ["on", "off", "unavailable"],
        "example_entity": "light.living_room"
    },
    "switch": {
        "description": "Simple on/off devices without dimming or color capabilities",
        "common_services": ["turn_on", "turn_off", "toggle"],
        "attributes": ["friendly_name", "icon", "device_class"],
        "states": ["on", "off", "unavailable"],
        "example_entity": "switch.kitchen_outlet"
    },
    "climate": {
        "description": "Temperature control devices like thermostats and HVAC systems",
        "common_services": ["set_temperature", "set_hvac_mode", "set_fan_mode"],
        "attributes": [
            "current_temperature", "target_temperature", "hvac_mode", 
            "fan_mode", "humidity", "supported_features"
        ],
        "states": ["heat", "cool", "auto", "off", "dry", "fan_only", "unavailable"],
        "example_entity": "climate.living_room_thermostat"
    },
    "sensor": {
        "description": "Devices that measure something and report a value (temperature, humidity, power)",
        "common_services": [],  # Sensors typically don't have services to call
        "attributes": ["unit_of_measurement", "device_class", "state_class"],
        "states": ["numeric values", "string values", "unavailable", "unknown"],
        "example_entity": "sensor.living_room_temperature"
    },
    "binary_sensor": {
        "description": "Sensors with binary states (on/off, detected/clear)",
        "common_services": [],  # Binary sensors typically don't have services to call
        "attributes": ["device_class", "off_delay"],
        "states": ["on", "off", "unavailable"],
        "example_entity": "binary_sensor.front_door_motion"
    },
    "cover": {
        "description": "Movable barriers like blinds, garage doors, or gates",
        "common_services": ["open_cover", "close_cover", "stop_cover", "set_cover_position"],
        "attributes": ["current_position", "current_tilt_position", "supported_features"],
        "states": ["open", "closed", "opening", "closing", "unavailable"],
        "example_entity": "cover.living_room_blinds"
    },
    "media_player": {
        "description": "Devices that play media like speakers, TVs, or receivers",
        "common_services": ["turn_on", "turn_off", "play_media", "media_play", "media_pause", "volume_set"],
        "attributes": [
            "media_content_id", "media_content_type", "media_title", 
            "media_artist", "volume_level", "supported_features"
        ],
        "states": ["playing", "paused", "idle", "off", "on", "unavailable"],
        "example_entity": "media_player.living_room_speaker"
    },
    "scene": {
        "description": "Predefined set of states for multiple entities",
        "common_services": ["turn_on"],
        "attributes": ["entity_id", "friendly_name"],
        "states": [],  # Scenes don't have states themselves
        "example_entity": "scene.movie_night"
    },
    "script": {
        "description": "Sequence of actions that can be triggered",
        "common_services": ["turn_on", "toggle", "reload"],
        "attributes": ["last_triggered", "mode", "current_step"],
        "states": ["on", "off"],
        "example_entity": "script.welcome_home"
    },
    "automation": {
        "description": "Rule that triggers actions based on events",
        "common_services": ["turn_on", "turn_off", "toggle", "trigger"],
        "attributes": ["last_triggered", "mode"],
        "states": ["on", "off"],
        "example_entity": "automation.turn_off_lights_when_away"
    }
}

# Common Service Parameters
SERVICE_PARAMETERS = {
    "light.turn_on": {
        "entity_id": "Entity ID of the light to control (e.g., light.living_room)",
        "brightness": "Brightness level from 0-255",
        "rgb_color": "RGB color as a list of 3 values [R, G, B] each 0-255",
        "color_temp": "Color temperature in mireds (lower is cooler/bluer)",
        "brightness_pct": "Brightness as a percentage 0-100",
        "transition": "Transition time in seconds",
        "effect": "Light effect from the available effect list"
    },
    "climate.set_temperature": {
        "entity_id": "Entity ID of the climate device to control",
        "temperature": "Target temperature in configured units",
        "target_temp_high": "High target temperature for range mode",
        "target_temp_low": "Low target temperature for range mode",
        "hvac_mode": "HVAC mode to set (optional)"
    }
}

# Entity Attributes Explanation
COMMON_ATTRIBUTES = {
    "friendly_name": "Human-readable name of the entity",
    "supported_features": "Bitmap of features supported by the entity",
    "device_class": "Type of device, affects icons and behavior",
    "unit_of_measurement": "Unit for numeric sensor values (°C, %, W, etc.)",
    "icon": "Icon used to represent the entity",
    "last_changed": "Timestamp when the state last changed",
    "last_updated": "Timestamp when the entity was last updated"
}

# Device Classes
DEVICE_CLASSES = {
    "binary_sensor": {
        "motion": "Motion detection",
        "door": "Door position (open/closed)",
        "window": "Window position (open/closed)",
        "presence": "Presence detection (home/away)",
        "battery": "Battery status (low/normal)",
        "light": "Light detection (light/dark)"
    },
    "sensor": {
        "temperature": "Temperature measurement",
        "humidity": "Humidity measurement",
        "pressure": "Pressure measurement",
        "power": "Power measurement",
        "energy": "Energy measurement",
        "illuminance": "Light level measurement"
    }
}

# Home Assistant API Structure
API_ENDPOINTS = {
    "/api/states": "Get all entity states or state of a specific entity",
    "/api/services": "Get available services or call a service",
    "/api/config": "Get configuration information",
    "/api/history/period": "Get historical state data",
    "/api/template": "Render a template",
    "/api/events": "Fire an event",
    "/api/logbook": "Get logbook entries"
}

# Home Assistant Template Examples
TEMPLATE_EXAMPLES = {
    "get_state": "{{ states('sensor.temperature') }}",
    "get_attribute": "{{ state_attr('light.living_room', 'brightness') }}",
    "conditional": "{% if is_state('binary_sensor.motion', 'on') %}Motion detected{% else %}No motion{% endif %}",
    "iterate_domain": "{% for light in states.light %}{{ light.entity_id }}: {{ light.state }}{% endfor %}",
    "filtered_entities": "{{ states.sensor | selectattr('state', 'lt', '20') | map(attribute='entity_id') | list }}"
}

# Common Error Patterns and Troubleshooting
TROUBLESHOOTING = {
    "entity_not_found": "Entity ID might be incorrect or the entity is unavailable",
    "service_not_found": "The service might not exist or the domain is incorrect",
    "integration_not_loaded": "The required integration is not set up in Home Assistant",
    "attribute_error": "The attribute doesn't exist for this entity",
    "permission_denied": "The token doesn't have sufficient permissions",
    "value_error": "The service parameter has an invalid value or type"
}

def get_domain_info(domain: str) -> dict:
    """
    Get information about a specific domain.
    
    Args:
        domain: Domain name (e.g., light, switch, climate)
        
    Returns:
        Dictionary with domain information
    """
    return DOMAINS.get(domain, {"description": "Unknown domain"})

def get_service_parameters(service: str) -> dict:
    """
    Get parameters for a specific service.
    
    Args:
        service: Service name including domain (e.g., light.turn_on)
        
    Returns:
        Dictionary with service parameters
    """
    return SERVICE_PARAMETERS.get(service, {})

def get_device_classes(domain: str) -> dict:
    """
    Get device classes for a specific domain.
    
    Args:
        domain: Domain name (e.g., binary_sensor, sensor)
        
    Returns:
        Dictionary with device classes
    """
    return DEVICE_CLASSES.get(domain, {}) 