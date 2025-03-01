"""
Common usage patterns for the Home Assistant API.

This module contains examples of common patterns for interacting with
Home Assistant through its API. These examples help agents understand
how to accomplish typical tasks.
"""

# Examples for controlling lights
LIGHT_CONTROL_EXAMPLES = {
    "turn_on_basic": {
        "description": "Turn on a light",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": "light.living_room"
        }
    },
    "turn_on_with_brightness": {
        "description": "Turn on a light with 50% brightness",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": "light.living_room",
            "brightness_pct": 50
        }
    },
    "turn_on_with_color": {
        "description": "Turn on a light with specific RGB color",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": "light.living_room",
            "rgb_color": [255, 0, 0]  # Red
        }
    },
    "turn_on_with_color_temp": {
        "description": "Turn on a light with specific color temperature",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": "light.living_room",
            "color_temp": 300  # Warm white
        }
    },
    "turn_on_with_transition": {
        "description": "Turn on a light with smooth transition",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": "light.living_room",
            "transition": 2  # 2 seconds
        }
    }
}

# Examples for controlling climate devices
CLIMATE_CONTROL_EXAMPLES = {
    "set_temperature": {
        "description": "Set temperature on a climate device",
        "service": "climate.set_temperature",
        "service_data": {
            "entity_id": "climate.living_room",
            "temperature": 22.5  # 22.5°C
        }
    },
    "set_hvac_mode": {
        "description": "Set HVAC mode on a climate device",
        "service": "climate.set_hvac_mode",
        "service_data": {
            "entity_id": "climate.living_room",
            "hvac_mode": "heat"  # Options: heat, cool, auto, off
        }
    },
    "set_fan_mode": {
        "description": "Set fan mode on a climate device",
        "service": "climate.set_fan_mode",
        "service_data": {
            "entity_id": "climate.living_room",
            "fan_mode": "auto"  # Options depend on the device
        }
    }
}

# Examples for controlling covers (blinds, shades, etc.)
COVER_CONTROL_EXAMPLES = {
    "open_cover": {
        "description": "Open a cover completely",
        "service": "cover.open_cover",
        "service_data": {
            "entity_id": "cover.living_room"
        }
    },
    "close_cover": {
        "description": "Close a cover completely",
        "service": "cover.close_cover",
        "service_data": {
            "entity_id": "cover.living_room"
        }
    },
    "set_cover_position": {
        "description": "Set a cover to a specific position",
        "service": "cover.set_cover_position",
        "service_data": {
            "entity_id": "cover.living_room",
            "position": 50  # 50% open
        }
    }
}

# Examples for getting entity states
STATE_QUERY_EXAMPLES = {
    "get_light_state": {
        "description": "Check if a light is on or off",
        "code": "entity_state = get_entity_state('light.living_room')\nstate = entity_state['state']  # 'on' or 'off'"
    },
    "get_temperature": {
        "description": "Get temperature from a sensor",
        "code": "entity_state = get_entity_state('sensor.living_room_temperature')\ntemperature = float(entity_state['state'])"
    },
    "check_motion": {
        "description": "Check if motion is detected",
        "code": "entity_state = get_entity_state('binary_sensor.living_room_motion')\nmotion_detected = entity_state['state'] == 'on'"
    }
}

# Examples for template usage
TEMPLATE_EXAMPLES = {
    "get_entity_state": {
        "description": "Get an entity's state value",
        "template": "{{ states('sensor.living_room_temperature') }}"
    },
    "get_attribute": {
        "description": "Get an entity's attribute",
        "template": "{{ state_attr('light.living_room', 'brightness') }}"
    },
    "check_state_condition": {
        "description": "Check if an entity is in a specific state",
        "template": "{{ is_state('binary_sensor.front_door', 'on') }}"
    },
    "comparison": {
        "description": "Compare a state value to a threshold",
        "template": "{{ states('sensor.living_room_temperature') | float > 22 }}"
    },
    "list_all_entities_in_domain": {
        "description": "List all entities in a domain that are on",
        "template": "{% for light in states.light if light.state == 'on' %}\n  {{ light.entity_id }}\n{% endfor %}"
    }
}

# Examples of advanced patterns
ADVANCED_PATTERNS = {
    "control_multiple_entities": {
        "description": "Control multiple entities in a single service call",
        "service": "light.turn_on",
        "service_data": {
            "entity_id": ["light.living_room", "light.kitchen", "light.hallway"],
            "brightness_pct": 75
        }
    },
    "control_entity_by_area": {
        "description": "Control all lights in an area",
        "steps": [
            "1. Get all light entities",
            "2. Filter those containing 'living_room' in their entity_id",
            "3. Call light.turn_on with the filtered list"
        ],
        "code": "states = get_states()\nliving_room_lights = [s['entity_id'] for s in states if s['entity_id'].startswith('light.') and 'living_room' in s['entity_id']]\ncall_service('light', 'turn_on', {'entity_id': living_room_lights})"
    },
    "automate_based_on_state_changes": {
        "description": "Create an automation that triggers when a state changes",
        "example": {
            "trigger": {
                "platform": "state",
                "entity_id": "binary_sensor.front_door",
                "to": "on"
            },
            "action": {
                "service": "light.turn_on",
                "entity_id": "light.entryway"
            }
        }
    }
}

# Examples of interpreting natural language commands
NLP_EXAMPLES = {
    "turn_on_light": {
        "natural_language": "Turn on the living room light",
        "interpretation": {
            "intent": "turn_on",
            "domain": "light",
            "location": "living room",
            "parameters": {}
        },
        "service_call": {
            "domain": "light",
            "service": "turn_on",
            "data": {
                "entity_id": "light.living_room"
            }
        }
    },
    "dim_lights": {
        "natural_language": "Dim the bedroom lights to 30%",
        "interpretation": {
            "intent": "adjust",
            "domain": "light",
            "location": "bedroom",
            "parameters": {
                "brightness": 30
            }
        },
        "service_call": {
            "domain": "light",
            "service": "turn_on",
            "data": {
                "entity_id": "light.bedroom",
                "brightness_pct": 30
            }
        }
    },
    "set_temperature": {
        "natural_language": "Set the living room thermostat to 72 degrees",
        "interpretation": {
            "intent": "set_temperature",
            "domain": "climate",
            "location": "living room",
            "parameters": {
                "temperature": 72
            }
        },
        "service_call": {
            "domain": "climate",
            "service": "set_temperature",
            "data": {
                "entity_id": "climate.living_room",
                "temperature": 22.2  # Converted to Celsius
            }
        }
    },
    "check_temperature": {
        "natural_language": "What's the temperature in the kitchen?",
        "interpretation": {
            "intent": "query",
            "domain": "sensor",
            "location": "kitchen",
            "parameters": {
                "attribute": "temperature"
            }
        },
        "api_call": "get_entity_state('sensor.kitchen_temperature')"
    }
}

def get_example_for_intent(intent: str, domain: str = None) -> dict:
    """
    Get an example for a specific intent and optional domain.
    
    Args:
        intent: The intent (turn_on, query, set_temperature, etc.)
        domain: Optional domain filter (light, climate, etc.)
        
    Returns:
        Dictionary with example information
    """
    for example_key, example in NLP_EXAMPLES.items():
        if example["interpretation"]["intent"] == intent:
            if domain is None or example["interpretation"]["domain"] == domain:
                return example
    
    return {"error": "No example found for the specified intent and domain"}

def get_service_example(domain: str, service: str) -> dict:
    """
    Get an example for a specific service.
    
    Args:
        domain: Service domain (light, climate, etc.)
        service: Service name (turn_on, set_temperature, etc.)
        
    Returns:
        Dictionary with example information
    """
    service_key = f"{domain}.{service}"
    
    # Check in light examples
    for example_key, example in LIGHT_CONTROL_EXAMPLES.items():
        if example["service"] == service_key:
            return example
    
    # Check in climate examples
    for example_key, example in CLIMATE_CONTROL_EXAMPLES.items():
        if example["service"] == service_key:
            return example
    
    # Check in cover examples
    for example_key, example in COVER_CONTROL_EXAMPLES.items():
        if example["service"] == service_key:
            return example
    
    return {"error": "No example found for the specified service"} 