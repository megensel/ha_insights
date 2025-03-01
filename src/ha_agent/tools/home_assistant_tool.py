"""
Home Assistant API tool for interacting with smart home devices.
"""
import json
from typing import Dict, List, Any, Optional, Union
import requests
from loguru import logger
from pydantic import Field
from crewai.tools import BaseTool

from .home_assistant_concepts import (
    DOMAINS, SERVICE_PARAMETERS, COMMON_ATTRIBUTES,
    get_domain_info, get_service_parameters
)


class HomeAssistantTool:
    """
    Tool for interacting with the Home Assistant API.
    Provides methods for querying device states and controlling devices.
    
    Home Assistant uses a RESTful API with the following key concepts:
    - Entities: Represent devices or values (e.g., light.living_room, sensor.temperature)
    - States: The current values and attributes of entities
    - Services: Actions that can be performed (e.g., turn_on, set_temperature)
    - Domains: Categories of entities (e.g., light, switch, climate)
    
    Entity IDs follow the format: domain.object_id
    Example: light.living_room, sensor.kitchen_temperature
    """
    
    def __init__(self, base_url: str, token: str):
        """
        Initialize the Home Assistant tool.
        
        Args:
            base_url: Base URL of the Home Assistant instance (e.g., http://192.168.1.10:8123)
            token: Long-lived access token for authentication
        """
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        logger.debug(f"Initialized Home Assistant tool with base URL: {base_url}")
        
        # Initialize BaseTool instances for each method
        self.get_states_tool = GetStatesTool(home_assistant=self)
        self.get_entity_state_tool = GetEntityStateTool(home_assistant=self)
        self.call_service_tool = CallServiceTool(home_assistant=self)
        self.get_devices_tool = GetDevicesTool(home_assistant=self)
        self.get_services_tool = GetServicesTool(home_assistant=self)
        self.get_history_tool = GetHistoryTool(home_assistant=self)
        self.render_template_tool = RenderTemplateTool(home_assistant=self)
        self.get_entity_registry_tool = GetEntityRegistryTool(home_assistant=self)
        self.get_domain_info_tool = GetDomainInfoTool(home_assistant=self)
        
        # Store domain data from last API call to minimize API requests
        self._cached_states = None
        self._cached_services = None
    
    def get_states(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all entity states from Home Assistant.
        
        Args:
            limit: Optional limit on the number of entities to return.
                  If provided, will prioritize important entities.
        
        Returns:
            List of entity state dictionaries, each containing:
            - entity_id: The unique identifier (e.g., light.living_room)
            - state: The current state value (e.g., "on", "off", "23.5")
            - attributes: Additional information about the entity
            - last_changed: Timestamp when the state last changed
            - last_updated: Timestamp when the entity was last updated
        
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            response = requests.get(f"{self.base_url}/api/states", headers=self.headers)
            response.raise_for_status()
            states = response.json()
            logger.debug(f"Retrieved {len(states)} entity states from Home Assistant")
            
            # Update cache
            self._cached_states = states
            
            # If limit is provided and there are more states than the limit,
            # filter to keep the most important entities
            if limit and len(states) > limit:
                logger.info(f"Limiting states to {limit} entities (from {len(states)} total)")
                
                # Define priority domains - these are typically more relevant for users
                priority_domains = [
                    "light", "switch", "climate", "media_player", "cover", "lock", 
                    "alarm_control_panel", "camera", "vacuum", "scene", "script"
                ]
                
                # Sort states by domain priority
                def get_priority(state):
                    entity_id = state["entity_id"]
                    domain = entity_id.split(".")[0]
                    
                    # Give highest priority to entities in priority domains
                    if domain in priority_domains:
                        return (0, domain, entity_id)
                    
                    # Give medium priority to sensors that are not unavailable
                    if domain == "sensor" and state["state"] != "unavailable":
                        return (1, domain, entity_id)
                    
                    # Give lowest priority to other entities
                    return (2, domain, entity_id)
                
                states = sorted(states, key=get_priority)
                states = states[:limit]
            
            return states
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get states from Home Assistant: {str(e)}")
            raise
    
    def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        """
        Get state of a specific entity.
        
        Args:
            entity_id: Entity ID (e.g., light.living_room)
            
        Returns:
            Entity state dictionary containing:
            - entity_id: The unique identifier
            - state: The current state value
            - attributes: Additional information specific to the entity type
              (e.g., brightness for lights, temperature for climate devices)
            - last_changed: Timestamp when the state last changed
            - last_updated: Timestamp when the entity was last updated
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/states/{entity_id}", 
                headers=self.headers
            )
            response.raise_for_status()
            state = response.json()
            logger.debug(f"Retrieved state for entity {entity_id}: {state['state']}")
            
            # Enrich with domain information if available
            domain = entity_id.split(".")[0]
            domain_info = get_domain_info(domain)
            if domain_info and "description" in domain_info:
                # Add domain-specific context for the agent
                state["_domain_context"] = {
                    "description": domain_info["description"],
                    "common_states": domain_info.get("states", []),
                    "common_attributes": domain_info.get("attributes", [])
                }
                
            return state
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get state for entity {entity_id}: {str(e)}")
            raise
    
    def call_service(
        self, 
        domain: str, 
        service: str, 
        service_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Call a Home Assistant service.
        
        Common services by domain:
        - light: turn_on, turn_off, toggle (service_data: entity_id, brightness, rgb_color)
        - switch: turn_on, turn_off, toggle (service_data: entity_id)
        - climate: set_temperature, set_hvac_mode (service_data: entity_id, temperature, hvac_mode)
        - cover: open_cover, close_cover, stop_cover (service_data: entity_id)
        - media_player: play_media, volume_set (service_data: entity_id, media_content_id)
        
        Args:
            domain: Service domain (e.g., light, switch, climate)
            service: Service to call (e.g., turn_on, turn_off, set_temperature)
            service_data: Service data dictionary containing parameters and target entities
            
        Returns:
            List of affected entities and their updated states
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        if service_data is None:
            service_data = {}
        
        # Get service parameter info for context
        service_key = f"{domain}.{service}"
        service_params = get_service_parameters(service_key)
        
        # Log service parameters for context
        if service_params:
            logger.debug(f"Service parameters for {service_key}: {json.dumps(service_params)}")
        
        try:
            url = f"{self.base_url}/api/services/{domain}/{service}"
            logger.debug(
                f"Calling service {domain}.{service} with data: "
                f"{json.dumps(service_data)}"
            )
            
            response = requests.post(
                url, 
                headers=self.headers, 
                json=service_data
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Successfully called service {domain}.{service}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call service {domain}.{service}: {str(e)}")
            raise
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices registered with Home Assistant.
        
        Devices represent the physical hardware, while entities represent their functionality.
        A single device (e.g., a smart bulb) might have multiple entities (light, sensor).
        
        Returns:
            List of device dictionaries containing:
            - id: Unique device identifier
            - name: Human-readable name
            - manufacturer: Device manufacturer
            - model: Device model
            - area_id: ID of the area/room where the device is located
            - entities: List of entities associated with this device
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/devices", 
                headers=self.headers
            )
            response.raise_for_status()
            devices = response.json()
            logger.debug(f"Retrieved {len(devices)} devices from Home Assistant")
            return devices
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get devices from Home Assistant: {str(e)}")
            raise
    
    def get_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available services from Home Assistant.
        
        Returns:
            Dictionary mapping domain names to services, where each service contains:
            - name: Service name
            - description: Service description
            - fields: Service parameters/fields
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/services", 
                headers=self.headers
            )
            response.raise_for_status()
            services = response.json()
            
            # Update cache
            self._cached_services = services
            
            logger.debug(f"Retrieved services from {len(services)} domains")
            return services
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get services from Home Assistant: {str(e)}")
            raise
    
    def get_history(
        self, 
        entity_id: str, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Get historical state data for an entity.
        
        Args:
            entity_id: Entity ID to get history for
            start_time: Start time in ISO format (e.g., "2023-01-01T00:00:00Z")
            end_time: End time in ISO format
            
        Returns:
            List of state changes for the entity, containing timestamps and state values
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            url = f"{self.base_url}/api/history/period"
            params = {"filter_entity_id": entity_id}
            
            if start_time:
                url = f"{url}/{start_time}"
            
            if end_time:
                params["end_time"] = end_time
                
            response = requests.get(
                url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            history = response.json()
            logger.debug(f"Retrieved history for entity {entity_id}")
            return history
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get history for entity {entity_id}: {str(e)}")
            raise
    
    def render_template(self, template: str) -> str:
        """
        Render a Home Assistant template.
        
        Templates are used to dynamically generate text using Home Assistant data.
        Example: "The temperature is {{ states('sensor.temperature') }} degrees"
        
        Args:
            template: The template string to render
            
        Returns:
            Rendered template result
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            url = f"{self.base_url}/api/template"
            response = requests.post(
                url,
                headers=self.headers,
                json={"template": template}
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Rendered template: {template[:50]}...")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to render template: {str(e)}")
            raise
    
    def get_entity_registry(self) -> List[Dict[str, Any]]:
        """
        Get the entity registry from Home Assistant.
        
        The entity registry contains metadata about entities, including:
        - Entity ID to device ID mappings
        - Customizations (names, icons, etc.)
        - Disabled state
        - Entity categories
        
        Returns:
            List of entity registry entries
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/config/entity_registry", 
                headers=self.headers
            )
            response.raise_for_status()
            entities = response.json()
            logger.debug(f"Retrieved {len(entities)} entities from entity registry")
            return entities
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get entity registry: {str(e)}")
            raise
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific domain.
        
        Combines service definitions and entities belonging to this domain.
        Also includes static information about the domain from the concepts module.
        
        Args:
            domain: The domain to get information for (e.g., light, switch)
            
        Returns:
            Dictionary containing domain information:
            - entities: List of entities in this domain
            - services: Available services for this domain
            - description: Domain description
            - common_states: Common state values for this domain
            - common_attributes: Common attributes for entities in this domain
            
        Raises:
            requests.exceptions.RequestException: If API requests fail
        """
        try:
            # Get domain info from concepts module
            domain_concepts = get_domain_info(domain)
            
            # Get real entities for this domain from Home Assistant
            if not self._cached_states:
                states = self.get_states()
            else:
                states = self._cached_states
                
            domain_entities = [s for s in states if s["entity_id"].split(".")[0] == domain]
            
            # Get available services for this domain
            if not self._cached_services:
                services = self.get_services()
            else:
                services = self._cached_services
                
            domain_services = services.get(domain, {})
            
            # Create domain info
            domain_info = {
                "domain": domain,
                "entities": domain_entities,
                "services": domain_services,
                "entity_count": len(domain_entities),
                "description": domain_concepts.get("description", "Unknown domain"),
                "common_states": domain_concepts.get("states", []),
                "common_attributes": domain_concepts.get("attributes", []),
                "common_services": domain_concepts.get("common_services", [])
            }
            
            logger.debug(f"Retrieved domain info for {domain}")
            return domain_info
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get domain info for {domain}: {str(e)}")
            raise
    
    def get_tools(self) -> List[BaseTool]:
        """Get all tools as a list to pass to an agent"""
        return [
            self.get_states_tool,
            self.get_entity_state_tool,
            self.call_service_tool,
            self.get_devices_tool,
            self.get_services_tool,
            self.get_history_tool,
            self.render_template_tool,
            self.get_entity_registry_tool,
            self.get_domain_info_tool
        ]


class GetStatesTool(BaseTool):
    """Tool for getting all entity states from Home Assistant"""
    name: str = "get_states"
    description: str = "Get all entity states from Home Assistant. Returns a list of all entities and their current states. You can specify a limit parameter to limit the number of entities returned."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, limit: Optional[int] = 50) -> str:
        """
        Run the tool
        
        Args:
            limit: Maximum number of entities to return. Default is 50.
                  Set to None to return all entities (may cause context window issues).
        """
        try:
            states = self.home_assistant.get_states(limit=limit)
            return json.dumps(states, indent=2)
        except Exception as e:
            return f"Error getting states: {str(e)}"


class GetEntityStateTool(BaseTool):
    """Tool for getting state of a specific entity from Home Assistant"""
    name: str = "get_entity_state"
    description: str = "Get state of a specific entity from Home Assistant. Requires entity_id parameter (e.g., light.living_room)."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, entity_id: str) -> str:
        """Run the tool"""
        try:
            state = self.home_assistant.get_entity_state(entity_id)
            return json.dumps(state, indent=2)
        except Exception as e:
            return f"Error getting state for entity {entity_id}: {str(e)}"


class CallServiceTool(BaseTool):
    """Tool for calling a Home Assistant service"""
    name: str = "call_service"
    description: str = (
        "Call a Home Assistant service. Requires domain (e.g., light), service (e.g., turn_on), "
        "and optional service_data as JSON string. Common services: light.turn_on, switch.toggle, "
        "climate.set_temperature, cover.open_cover, media_player.play_media."
    )
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, argument: str) -> str:
        """Run the tool"""
        try:
            # Parse argument as JSON with domain, service, and optional service_data
            args = json.loads(argument)
            domain = args.get("domain")
            service = args.get("service")
            service_data = args.get("service_data", {})
            
            if not domain or not service:
                return "Error: domain and service parameters are required"
            
            result = self.home_assistant.call_service(domain, service, service_data)
            return json.dumps(result, indent=2)
        except json.JSONDecodeError:
            return "Error: argument must be a valid JSON string with domain and service fields"
        except Exception as e:
            return f"Error calling service: {str(e)}"


class GetDevicesTool(BaseTool):
    """Tool for getting all devices from Home Assistant"""
    name: str = "get_devices"
    description: str = "Get all devices registered with Home Assistant. Devices represent physical hardware while entities represent functionality. A single device may have multiple entities."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, argument: str = "") -> str:
        """Run the tool"""
        try:
            devices = self.home_assistant.get_devices()
            return json.dumps(devices, indent=2)
        except Exception as e:
            return f"Error getting devices: {str(e)}"


class GetServicesTool(BaseTool):
    """Tool for getting all available services from Home Assistant"""
    name: str = "get_services"
    description: str = "Get all available services from Home Assistant, organized by domain. This helps understand what actions can be performed in the system."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, argument: str = "") -> str:
        """Run the tool"""
        try:
            services = self.home_assistant.get_services()
            return json.dumps(services, indent=2)
        except Exception as e:
            return f"Error getting services: {str(e)}"


class GetHistoryTool(BaseTool):
    """Tool for getting historical state data for an entity"""
    name: str = "get_history"
    description: str = "Get historical state data for an entity. Requires entity_id and optional start_time and end_time in ISO format."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, argument: str) -> str:
        """Run the tool"""
        try:
            # Parse argument as JSON with entity_id and optional start_time/end_time
            args = json.loads(argument)
            entity_id = args.get("entity_id")
            start_time = args.get("start_time")
            end_time = args.get("end_time")
            
            if not entity_id:
                return "Error: entity_id parameter is required"
            
            history = self.home_assistant.get_history(entity_id, start_time, end_time)
            return json.dumps(history, indent=2)
        except json.JSONDecodeError:
            return "Error: argument must be a valid JSON string with entity_id field"
        except Exception as e:
            return f"Error getting history: {str(e)}"


class RenderTemplateTool(BaseTool):
    """Tool for rendering a Home Assistant template"""
    name: str = "render_template"
    description: str = (
        "Render a Home Assistant template. Templates use a Jinja2-based syntax to access Home Assistant data. "
        "Examples: '{{ states(\"sensor.temperature\") }}' or '{{ states.light | selectattr(\"state\", \"eq\", \"on\") | list }}'."
    )
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, template: str) -> str:
        """Run the tool"""
        try:
            result = self.home_assistant.render_template(template)
            return result
        except Exception as e:
            return f"Error rendering template: {str(e)}"


class GetEntityRegistryTool(BaseTool):
    """Tool for getting the entity registry from Home Assistant"""
    name: str = "get_entity_registry"
    description: str = "Get the entity registry from Home Assistant, which contains metadata about entities including customizations, device mappings, and disabled state."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, argument: str = "") -> str:
        """Run the tool"""
        try:
            entities = self.home_assistant.get_entity_registry()
            return json.dumps(entities, indent=2)
        except Exception as e:
            return f"Error getting entity registry: {str(e)}"


class GetDomainInfoTool(BaseTool):
    """Tool for getting comprehensive information about a specific domain"""
    name: str = "get_domain_info"
    description: str = "Get detailed information about a specific domain, including entities, services, and common attributes. Requires domain name (e.g., light, switch, climate)."
    home_assistant: Any = Field(description="Home Assistant tool instance")
    
    def _run(self, domain: str) -> str:
        """Run the tool"""
        try:
            domain_info = self.home_assistant.get_domain_info(domain)
            return json.dumps(domain_info, indent=2)
        except Exception as e:
            return f"Error getting domain info for {domain}: {str(e)}" 