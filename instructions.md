# Home Assistant Agent with Crew AI

## Project Overview
Create an intelligent agent system using Python and Crew AI that can interact with the Home Assistant API to control and automate smart home devices. The system should be able to switch between local Ollama models and cloud-based Anthropic models as needed.

## Technical Requirements
- Python 3.9+
- Crew AI for agent orchestration
- Home Assistant API integration
- Ollama for local AI model inference
- Anthropic API for cloud-based AI capabilities
- Proper error handling and logging
- Asynchronous capabilities for responsive home automation
- Model switching mechanism based on task requirements

## Core Features
1. Connect to Home Assistant API using authentication tokens
2. Query device states and sensor readings
3. Control devices (lights, switches, thermostats, etc.)
4. Create automation sequences triggered by specific conditions
5. Implement natural language processing for command interpretation
6. Provide feedback on command execution status
7. Dynamically switch between Ollama (local) and Anthropic (cloud) models
8. Select appropriate model based on task complexity and latency requirements

## Implementation Guide

### Step 1: Set up the environment
```python
# Import necessary libraries
import os
from crewai import Agent, Task, Crew
from crewai.models import OllamaModel, AnthropicModel
from dotenv import load_dotenv
import requests
import asyncio

# Load environment variables
load_dotenv()

# Home Assistant API configuration
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

# Model API keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize model providers
ollama_model = OllamaModel(model="llama3")  # Or your preferred Ollama model
anthropic_model = AnthropicModel(api_key=ANTHROPIC_API_KEY, model="claude-3-opus")  # Or your preferred Anthropic model
```

### Step 2: Create Home Assistant API Tool
```python
class HomeAssistantTool:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_states(self):
        """Get all entity states from Home Assistant"""
        response = requests.get(f"{self.base_url}/api/states", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_entity_state(self, entity_id):
        """Get state of a specific entity"""
        response = requests.get(f"{self.base_url}/api/states/{entity_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def call_service(self, domain, service, service_data=None):
        """Call a Home Assistant service"""
        if service_data is None:
            service_data = {}
        
        url = f"{self.base_url}/api/services/{domain}/{service}"
        response = requests.post(url, headers=self.headers, json=service_data)
        response.raise_for_status()
        return response.json()
```

### Step 3: Create Model Switching Mechanism
```python
class ModelSwitcher:
    def __init__(self, local_model, cloud_model):
        self.local_model = local_model
        self.cloud_model = cloud_model
        self.current_model = local_model  # Default to local model
    
    def select_model(self, task_complexity, latency_sensitive=False, force_model=None):
        """
        Select appropriate model based on task requirements
        
        Args:
            task_complexity: int from 1-10 indicating complexity
            latency_sensitive: bool indicating if task needs fast response
            force_model: str "local" or "cloud" to override automatic selection
        
        Returns:
            Selected model instance
        """
        if force_model == "local":
            self.current_model = self.local_model
            return self.local_model
        
        if force_model == "cloud":
            self.current_model = self.cloud_model
            return self.cloud_model
        
        # Automatic selection based on task requirements
        if task_complexity > 7 and not latency_sensitive:
            # Complex tasks use cloud model for better quality
            self.current_model = self.cloud_model
        elif latency_sensitive or task_complexity < 5:
            # Time-sensitive or simple tasks use local model
            self.current_model = self.local_model
        else:
            # Medium complexity, non-latency-sensitive tasks
            # Default to local to save on API costs
            self.current_model = self.local_model
            
        return self.current_model
    
    def get_current_model(self):
        return self.current_model

# Initialize the model switcher
model_switcher = ModelSwitcher(ollama_model, anthropic_model)
```

### Step 4: Define Crew AI Agents with Model Switching
```python
# Initialize the Home Assistant tool
ha_tool = HomeAssistantTool(HA_URL, HA_TOKEN)

# Create the Home Controller Agent (simple, frequent tasks - default to local model)
home_controller = Agent(
    role="Home Controller",
    goal="Control smart home devices efficiently and reliably",
    backstory="I am an AI agent specialized in home automation and IoT device control.",
    tools=[ha_tool.get_states, ha_tool.get_entity_state, ha_tool.call_service],
    llm=model_switcher.select_model(task_complexity=4, latency_sensitive=True),
    verbose=True
)

# Create the Analysis Agent (complex analysis - uses cloud model)
home_analyzer = Agent(
    role="Home Analyzer",
    goal="Analyze smart home data and recommend optimal actions",
    backstory="I analyze patterns in smart home usage to optimize comfort and energy efficiency.",
    tools=[ha_tool.get_states],
    llm=model_switcher.select_model(task_complexity=8, latency_sensitive=False),
    verbose=True
)

# Create the NLP Agent (medium complexity - could use either)
nlp_processor = Agent(
    role="Command Interpreter",
    goal="Interpret natural language commands accurately",
    backstory="I translate human instructions into specific device control commands.",
    llm=model_switcher.select_model(task_complexity=6),
    verbose=True
)
```

### Step 5: Define Tasks
```python
# Task for controlling lights
control_lights_task = Task(
    description="Turn on/off lights based on user request or sensor data",
    agent=home_controller,
    expected_output="Confirmation that lights were controlled appropriately"
)

# Task for adjusting temperature
control_climate_task = Task(
    description="Adjust thermostat settings for optimal comfort and energy efficiency",
    agent=home_controller,
    expected_output="Confirmation that climate settings were adjusted"
)

# Task for analyzing home state (complex task - uses cloud model)
analyze_home_task = Task(
    description="Analyze the current state of all home devices and sensors",
    agent=home_analyzer,
    expected_output="Summary of home state and recommendations for optimization"
)

# Task for interpreting voice commands
interpret_command_task = Task(
    description="Interpret natural language command and convert to specific actions",
    agent=nlp_processor,
    expected_output="Structured command ready for execution"
)
```

### Step 6: Create the Crew
```python
# Create the Home Assistant Crew
home_crew = Crew(
    agents=[home_controller, home_analyzer, nlp_processor],
    tasks=[control_lights_task, control_climate_task, analyze_home_task, interpret_command_task],
    verbose=2
)

# Run the crew
result = home_crew.kickoff()
print(result)
```

### Step 7: Example of Manual Model Switching
```python
# Function to manually switch models based on specific needs
def switch_agent_model(agent, model_type, task_complexity=5, latency_sensitive=False):
    """
    Manually switch an agent's model
    
    Args:
        agent: CrewAI Agent instance
        model_type: "local" or "cloud" or None (for automatic selection)
        task_complexity: Only used for automatic selection
        latency_sensitive: Only used for automatic selection
    """
    if model_type in ["local", "cloud"]:
        agent.llm = model_switcher.select_model(
            task_complexity=task_complexity, 
            latency_sensitive=latency_sensitive,
            force_model=model_type
        )
    else:
        agent.llm = model_switcher.select_model(
            task_complexity=task_complexity,
            latency_sensitive=latency_sensitive
        )
    
    print(f"Switched {agent.role} to {'Ollama' if agent.llm == ollama_model else 'Anthropic'} model")

# Example usage:
# switch_agent_model(home_analyzer, "cloud")  # Force cloud model
# switch_agent_model(home_controller, "local")  # Force local model
# switch_agent_model(nlp_processor, None, 8, False)  # Auto-select based on new requirements
```

## Extension Ideas
- Add a machine learning component to predict user preferences
- Implement voice command capabilities
- Create a dashboard for visualizing home data
- Add scheduling functionality for recurring tasks
- Implement user profiles for personalized automation
- Develop fallback mechanisms when one model type is unavailable
- Create a hybrid inference approach that combines local and cloud models
- Implement caching for frequent commands to reduce latency and API costs

## Project Challenges
- Ensure proper error handling for API connection issues
- Handle different device types and capabilities
- Implement secure authentication
- Create a responsive and user-friendly interface
- Balance automation with user control
- Manage latency differences between local and cloud models
- Handle network connectivity issues gracefully
- Optimize model selection for cost efficiency vs. performance

## Success Criteria
- Agent can reliably control Home Assistant devices
- Natural language commands are correctly interpreted
- System responds appropriately to changing home conditions
- Error handling prevents system failures
- User can easily understand and interact with the agent
- Model switching occurs seamlessly without user disruption
- Local models are used for time-sensitive tasks
- Cloud models are used for complex reasoning when appropriate