"""
Agent definitions for Home Assistant Agent.
Defines the specialized AI agents for different home automation tasks.
"""
from typing import Any, Dict, List, Optional
from crewai import Agent
from loguru import logger

from ..tools import HomeAssistantTool
from ..models import ModelSwitcher


def create_home_controller(
    model_switcher: ModelSwitcher,
    ha_tool: HomeAssistantTool,
    task_complexity: int = 4,
    latency_sensitive: bool = True
) -> Agent:
    """
    Create the Home Controller Agent (for simple, frequent tasks).
    
    This agent is responsible for direct control of Home Assistant devices.
    It understands how to call Home Assistant services, get entity states,
    and perform actions on devices using the API.
    
    Args:
        model_switcher: Model switcher instance
        ha_tool: HomeAssistantTool instance
        task_complexity: Task complexity (1-10)
        latency_sensitive: Whether this agent handles latency-sensitive tasks
        
    Returns:
        Configured Agent instance
    """
    # Select appropriate model based on task requirements
    model = model_switcher.select_model(
        task_complexity=task_complexity,
        latency_sensitive=latency_sensitive
    )
    
    agent = Agent(
        role="Home Controller",
        goal="Control smart home devices efficiently and reliably",
        backstory=(
            "I am an AI agent specialized in home automation and IoT device control. "
            "I understand how to interact with various smart home devices and can "
            "execute precise commands to control lights, switches, thermostats, and other devices. "
            "\n\n"
            "I know that Home Assistant uses entity IDs in the format of 'domain.object_id', "
            "such as 'light.living_room' or 'climate.bedroom'. When controlling devices, "
            "I use the appropriate services for each domain (e.g., light.turn_on, switch.toggle) "
            "and include the necessary parameters like brightness, color, or temperature settings."
        ),
        tools=[
            ha_tool.get_states_tool,
            ha_tool.get_entity_state_tool,
            ha_tool.call_service_tool,
            ha_tool.get_devices_tool,
            ha_tool.get_services_tool,
            ha_tool.get_entity_registry_tool
        ],
        llm=model,
        verbose=True
    )
    
    logger.info(
        f"Created Home Controller agent using "
        f"{'local' if model_switcher.get_model_type() == 'local' else 'cloud'} model"
    )
    
    return agent


def create_home_analyzer(
    model_switcher: ModelSwitcher,
    ha_tool: HomeAssistantTool,
    task_complexity: int = 4,
    latency_sensitive: bool = True
) -> Agent:
    """
    Create the Home Analyzer Agent (for complex analysis tasks).
    
    This agent specializes in analyzing Home Assistant data, including:
    - Sensor readings and trends
    - Device states and usage patterns
    - Historical data for entities
    - Relationships between different entities
    - Creating automation suggestions
    
    Args:
        model_switcher: Model switcher instance
        ha_tool: HomeAssistantTool instance
        task_complexity: Task complexity (1-10)
        latency_sensitive: Whether this agent handles latency-sensitive tasks
        
    Returns:
        Configured Agent instance
    """
    # TEMPORARY: Forcing local model for all agents while troubleshooting Ollama
    model = model_switcher.select_model(
        task_complexity=task_complexity,
        latency_sensitive=latency_sensitive
    )
    
    agent = Agent(
        role="Home Analyzer",
        goal="Analyze smart home data and recommend optimal actions",
        backstory=(
            "I analyze patterns in smart home usage to optimize comfort and energy efficiency. "
            "By examining historical data, device states, and environmental conditions, "
            "I can identify trends, anomalies, and opportunities for automation improvements. "
            "\n\n"
            "I understand Home Assistant's data structure where entities represent device states, "
            "attributes provide additional details, and historical data shows patterns over time. "
            "I can analyze sensor readings from various domains (temperature, humidity, motion, etc.) "
            "and correlate them with device states to identify patterns and optimization opportunities. "
            "I'm also familiar with Home Assistant's templating system, which allows for "
            "dynamic expressions and data transformations."
        ),
        tools=[
            ha_tool.get_states_tool,
            ha_tool.get_history_tool,
            ha_tool.get_devices_tool,
            ha_tool.render_template_tool,
            ha_tool.get_entity_registry_tool,
            ha_tool.get_services_tool
        ],
        llm=model,
        verbose=True
    )
    
    logger.info(
        f"Created Home Analyzer agent using "
        f"{'local' if model_switcher.get_model_type() == 'local' else 'cloud'} model"
    )
    
    return agent


def create_nlp_processor(
    model_switcher: ModelSwitcher,
    task_complexity: int = 4,
    latency_sensitive: bool = True
) -> Agent:
    """
    Create the NLP Processor Agent (for interpreting natural language commands).
    
    This agent specializes in:
    - Parsing natural language commands
    - Identifying intents (turn on/off, adjust, query)
    - Extracting entity references from common language
    - Converting ambiguous terms to specific entity IDs
    - Determining parameters for services (brightness, color, temperature)
    
    Args:
        model_switcher: Model switcher instance
        task_complexity: Task complexity (1-10)
        latency_sensitive: Whether this agent handles latency-sensitive tasks
        
    Returns:
        Configured Agent instance
    """
    # TEMPORARY: Forcing local model for all agents while troubleshooting Ollama
    model = model_switcher.select_model(
        task_complexity=task_complexity,
        latency_sensitive=latency_sensitive
    )
    
    agent = Agent(
        role="Command Interpreter",
        goal="Interpret natural language commands accurately",
        backstory=(
            "I translate human instructions into specific device control commands. "
            "I understand various ways people might refer to their smart home devices "
            "and can extract intents, targets, and parameters from natural language requests. "
            "\n\n"
            "I'm familiar with Home Assistant's entity naming conventions and can map common "
            "phrases like 'living room light' to specific entity IDs like 'light.living_room'. "
            "I can interpret various command types including direct actions ('turn on the lights'), "
            "queries ('what's the temperature?'), adjustments ('make it cooler'), "
            "and complex requests ('turn on the lights if someone's home')."
        ),
        llm=model,
        verbose=True
    )
    
    logger.info(
        f"Created Command Interpreter agent using "
        f"{'local' if model_switcher.get_model_type() == 'local' else 'cloud'} model"
    )
    
    return agent 