"""
Task definitions for Home Assistant Agent.
Defines tasks that can be performed by the agents.
"""
from typing import Dict, List, Any, Optional
from crewai import Task, Agent


def create_control_lights_task(
    agent: Agent,
    command: Optional[str] = None
) -> Task:
    """
    Create a task for controlling lights.
    
    Args:
        agent: Agent to perform the task (typically home_controller)
        command: Optional specific command to include in task description
        
    Returns:
        Configured Task instance
    """
    description = (
        "Control lighting devices in Home Assistant based on user request or sensor data. "
        "Light entities have the domain 'light' and support services like 'light.turn_on', "
        "'light.turn_off', and 'light.toggle'. When turning lights on, you can specify "
        "attributes like brightness (0-255), color (RGB), color temperature, transition duration, etc."
    )
    
    if command:
        description = f"{description}\n\nCommand to interpret and execute: '{command}'"
        
    return Task(
        description=description,
        agent=agent,
        expected_output=(
            "Confirmation that lights were controlled appropriately, including: "
            "1. Which light entities were affected (using their entity_ids) "
            "2. What state changes were made (on/off, brightness, color) "
            "3. The exact service called (e.g., light.turn_on) with parameters "
            "4. Whether there were any issues or errors during execution"
        )
    )


def create_control_climate_task(
    agent: Agent,
    command: Optional[str] = None
) -> Task:
    """
    Create a task for controlling climate devices.
    
    Args:
        agent: Agent to perform the task (typically home_controller)
        command: Optional specific command to include in task description
        
    Returns:
        Configured Task instance
    """
    description = (
        "Adjust climate devices in Home Assistant for comfort and energy efficiency. "
        "Climate entities have the domain 'climate' and support services like "
        "'climate.set_temperature', 'climate.set_hvac_mode', and 'climate.set_fan_mode'. "
        "Climate devices have attributes like current_temperature, target_temperature, hvac_mode "
        "(heat, cool, auto, off), fan_mode, and humidity."
    )
    
    if command:
        description = f"{description}\n\nCommand to interpret and execute: '{command}'"
        
    return Task(
        description=description,
        agent=agent,
        expected_output=(
            "Confirmation that climate settings were adjusted, including: "
            "1. Which climate entities were affected (using their entity_ids) "
            "2. What temperature or mode changes were made "
            "3. The exact service called (e.g., climate.set_temperature) with parameters "
            "4. Current state of the affected devices after changes"
        )
    )


def create_analyze_home_task(
    agent: Agent,
    query: Optional[str] = None,
    specific_entities: Optional[List[str]] = None
) -> Task:
    """
    Create a task for analyzing home state.
    
    Args:
        agent: Agent to perform the task (typically home_analyzer)
        query: Natural language query about the home state
        specific_entities: Optional list of entity IDs to focus analysis on
        
    Returns:
        Configured Task instance
    """
    description = (
        "Analyze the current state of Home Assistant entities to provide insights about the home. "
        "Consider relationships between different entity types, such as: "
        "- Sensor readings (temperature, humidity, motion, light level) "
        "- Device states (lights, switches, climate, media players) "
        "- Environmental conditions (weather, time of day, season) "
        "- Historical patterns and trends over time "
        "\n\n"
        "Pay attention to Home Assistant attributes for each entity, which often contain "
        "valuable additional data beyond the primary state value."
    )
    
    if query:
        description = f"{description}\n\nAnswer this specific query: '{query}'"
        if specific_entities:
            entities_str = ", ".join(specific_entities)
            description += f"\n\nFocus on these specific entities: {entities_str}"
    else:
        if specific_entities:
            entities_str = ", ".join(specific_entities)
            description = f"{description}\n\nFocus on these specific entities: {entities_str}"
        
    return Task(
        description=description,
        agent=agent,
        expected_output=(
            "Summary of home state and recommendations or answers to the query, including: "
            "1. Current state overview of relevant entities with their entity_ids "
            "2. Analysis of patterns or anomalies detected in the data "
            "3. Relevant attribute values that provide context "
            "4. Specific answers to the user's query if provided "
            "5. Recommendations for automation or optimization if appropriate"
        )
    )


def create_interpret_command_task(
    agent: Agent,
    user_command: str
) -> Task:
    """
    Create a task for interpreting a natural language command.
    
    Args:
        agent: Agent to perform the task (typically nlp_processor)
        user_command: Natural language command from the user
        
    Returns:
        Configured Task instance
    """
    return Task(
        description=(
            f"Interpret this natural language command: '{user_command}'\n\n"
            "Extract the following information from the command: "
            "1. Primary intent (e.g., turn_on, turn_off, set_temperature, get_state) "
            "2. Target entity type (light, switch, climate, sensor, etc.) "
            "3. Location or specific device identifier (living room, bedroom, kitchen, etc.) "
            "4. Parameters or settings (brightness level, color, temperature value) "
            "5. Conditions or constraints (if present) "
            "\n\n"
            "Map vague terms to specific Home Assistant concepts. For example: "
            "- 'Turn on the lights in the living room' → domain: light, service: turn_on, area: living room "
            "- 'Make it cooler' → domain: climate, service: set_temperature, direction: decrease "
            "- 'Is anyone home?' → domain: binary_sensor, type: presence/occupancy"
        ),
        agent=agent,
        expected_output=(
            "Structured command interpretation, including: "
            "1. Identified intent (e.g., turn_on, turn_off, adjust, query) "
            "2. Target domains and potential entity_ids "
            "3. Parameters or settings with specific values when applicable "
            "4. Confidence level in the interpretation "
            "5. Suggested Home Assistant service to call with parameters"
        )
    )


def create_device_discovery_task(agent: Agent) -> Task:
    """
    Create a task for discovering and cataloging devices.
    
    Args:
        agent: Agent to perform the task
        
    Returns:
        Configured Task instance
    """
    return Task(
        description=(
            "Discover and catalog all available devices and entities in the Home Assistant instance. "
            "Organize them by domain type and functionality, identifying: "
            "1. Light entities and their capabilities (brightness, color, effects) "
            "2. Climate devices and supported features (heat, cool, fan modes) "
            "3. Sensors and their measurement types (temperature, humidity, motion) "
            "4. Switches, covers, media players, and other controllable devices "
            "5. Areas/rooms where devices are located "
            "\n\n"
            "For each entity, determine what services can be called and what attributes are available. "
            "Pay attention to entity attributes that indicate supported features."
        ),
        agent=agent,
        expected_output=(
            "Comprehensive inventory of available devices and entities, including: "
            "1. List of all entities organized by domain type "
            "2. Capabilities and supported features of each entity "
            "3. Current state information and important attributes "
            "4. Available services that can be called for each domain "
            "5. Recommendations for logical device grouping by area/function"
        )
    )


def create_create_automation_task(
    agent: Agent,
    automation_description: str
) -> Task:
    """
    Create a task for creating an automation sequence.
    
    Args:
        agent: Agent to perform the task
        automation_description: Description of the desired automation
        
    Returns:
        Configured Task instance
    """
    return Task(
        description=(
            f"Create a Home Assistant automation based on this description: '{automation_description}'\n\n"
            "An automation in Home Assistant consists of: "
            "1. Trigger(s) - what starts the automation (time, state change, event) "
            "2. Condition(s) - optional checks before execution (if applicable) "
            "3. Action(s) - services to call when the automation runs "
            "\n\n"
            "Consider entity relationships, time patterns, and state conditions. "
            "Design the automation to be reliable, intuitive, and avoid potential issues "
            "like infinite loops or conflicting actions."
        ),
        agent=agent,
        expected_output=(
            "Detailed automation configuration, including: "
            "1. Trigger conditions with specific entity_ids and values "
            "2. Condition checks if needed "
            "3. Actions with service calls and parameters "
            "4. YAML configuration ready for Home Assistant "
            "5. Explanation of how the automation works and any limitations"
        )
    ) 