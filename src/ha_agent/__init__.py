"""
Home Assistant Agent package.
Main package for controlling Home Assistant through Crew AI agents.
"""
import os
from loguru import logger
import sys

# Set up logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL)

# Import and expose key components
from .models import ModelSwitcher
from .tools import HomeAssistantTool
from .tools.home_assistant_concepts import (
    DOMAINS, SERVICE_PARAMETERS, COMMON_ATTRIBUTES,
    DEVICE_CLASSES, API_ENDPOINTS, TEMPLATE_EXAMPLES,
    TROUBLESHOOTING, get_domain_info, get_service_parameters, get_device_classes
)
from .tools.common_patterns import (
    LIGHT_CONTROL_EXAMPLES, CLIMATE_CONTROL_EXAMPLES,
    COVER_CONTROL_EXAMPLES, STATE_QUERY_EXAMPLES,
    TEMPLATE_EXAMPLES as TEMPLATE_USAGE_EXAMPLES,
    ADVANCED_PATTERNS, NLP_EXAMPLES,
    get_example_for_intent, get_service_example
)
from .agents import (
    create_home_controller,
    create_home_analyzer,
    create_nlp_processor
)
from .tasks import (
    create_control_lights_task,
    create_control_climate_task,
    create_analyze_home_task,
    create_interpret_command_task,
    create_device_discovery_task,
    create_create_automation_task
)

__all__ = [
    "ModelSwitcher",
    "HomeAssistantTool",
    "create_home_controller",
    "create_home_analyzer",
    "create_nlp_processor",
    "create_control_lights_task",
    "create_control_climate_task",
    "create_analyze_home_task",
    "create_interpret_command_task",
    "create_device_discovery_task",
    "create_create_automation_task",
    # Home Assistant concepts
    "DOMAINS",
    "SERVICE_PARAMETERS",
    "COMMON_ATTRIBUTES",
    "DEVICE_CLASSES",
    "API_ENDPOINTS",
    "TEMPLATE_EXAMPLES",
    "TROUBLESHOOTING",
    "get_domain_info",
    "get_service_parameters",
    "get_device_classes",
    # Common patterns
    "LIGHT_CONTROL_EXAMPLES",
    "CLIMATE_CONTROL_EXAMPLES",
    "COVER_CONTROL_EXAMPLES",
    "STATE_QUERY_EXAMPLES",
    "TEMPLATE_USAGE_EXAMPLES",
    "ADVANCED_PATTERNS",
    "NLP_EXAMPLES",
    "get_example_for_intent",
    "get_service_example"
]

# Version information
__version__ = '0.1.0' 