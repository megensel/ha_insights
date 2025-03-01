"""
Basic example of using Home Assistant Agent.
"""
import os
from dotenv import load_dotenv
from crewai import Crew, LLM
from loguru import logger

# Add the parent directory to the path so we can import the ha_agent package
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ha_agent import (
    ModelSwitcher,
    HomeAssistantTool,
    create_home_controller,
    create_home_analyzer,
    create_nlp_processor,
    create_control_lights_task,
    create_analyze_home_task,
    create_interpret_command_task
)


def main():
    """Run a basic example of Home Assistant Agent"""
    # Load environment variables
    load_dotenv()
    
    # Get environment variables
    ha_url = os.getenv("HA_URL")
    ha_token = os.getenv("HA_TOKEN")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    
    # Validate required environment variables
    if not ha_url or not ha_token:
        logger.error("HA_URL and HA_TOKEN must be set in environment variables or .env file")
        sys.exit(1)
    
    # Initialize models
    logger.info("Initializing models...")
    
    # Check if MOCK_LOCAL_MODEL is set in environment
    use_mock = os.getenv("MOCK_LOCAL_MODEL", "").lower() in ("true", "1", "yes")
    
    if use_mock:
        logger.info("Using mock model (Ollama not required)")
        # Create a simple mock model using the same LLM class
        from crewai.utilities.mock_llm import MockLLM
        ollama_model = MockLLM()
        anthropic_model = MockLLM()
    else:
        ollama_model = LLM(
            model="ollama/llama3",
            base_url=ollama_base_url
        )
        
        # TEMPORARY: Using Ollama for both local and cloud models (Anthropic disabled)
        anthropic_model = ollama_model
        logger.info("Using Ollama for both local and cloud models")
    
    # Initialize model switcher
    model_switcher = ModelSwitcher(
        local_model=ollama_model,
        cloud_model=anthropic_model
    )
    
    # Initialize Home Assistant tool
    logger.info(f"Connecting to Home Assistant at {ha_url}...")
    ha_tool = HomeAssistantTool(
        base_url=ha_url,
        token=ha_token
    )
    
    # Create agents
    logger.info("Creating agents...")
    home_controller = create_home_controller(
        model_switcher=model_switcher,
        ha_tool=ha_tool
    )
    
    home_analyzer = create_home_analyzer(
        model_switcher=model_switcher,
        ha_tool=ha_tool
    )
    
    nlp_processor = create_nlp_processor(
        model_switcher=model_switcher
    )
    
    # Create tasks
    logger.info("Creating tasks...")
    
    # Example 1: Analyze home state
    analyze_task = create_analyze_home_task(
        agent=home_analyzer
    )
    
    # Example 2: Process and execute a command
    user_command = "Turn on the kitchen lights"
    
    interpret_task = create_interpret_command_task(
        agent=nlp_processor,
        user_command=user_command
    )
    
    control_task = create_control_lights_task(
        agent=home_controller,
        command=user_command
    )
    
    # Create crew for analysis
    logger.info("Running home analysis...")
    analysis_crew = Crew(
        agents=[home_analyzer],
        tasks=[analyze_task],
        verbose=True
    )
    
    # Run analysis
    analysis_result = analysis_crew.kickoff()
    logger.info("Analysis complete")
    print("\n=== Analysis Result ===")
    print(analysis_result)
    
    # Create crew for command interpretation and execution
    logger.info(f"Processing command: '{user_command}'...")
    command_crew = Crew(
        agents=[nlp_processor, home_controller],
        tasks=[interpret_task, control_task],
        verbose=True
    )
    
    # Run command processing
    command_result = command_crew.kickoff()
    logger.info("Command processing complete")
    print("\n=== Command Result ===")
    print(command_result)


if __name__ == "__main__":
    main() 