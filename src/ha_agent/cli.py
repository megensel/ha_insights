"""
Command-line interface for Home Assistant Agent.
Provides commands for controlling Home Assistant through Crew AI agents.
"""
import os
import argparse
import asyncio
import sys
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from crewai import Crew, LLM
from loguru import logger

from . import (
    ModelSwitcher,
    HomeAssistantTool,
    create_home_controller,
    create_home_analyzer,
    create_nlp_processor,
    create_control_lights_task,
    create_analyze_home_task,
    create_interpret_command_task,
    create_device_discovery_task,
    create_control_climate_task,
    create_create_automation_task
)


def load_config():
    """Load configuration from environment variables"""
    load_dotenv()
    
    # Required configuration
    ha_url = os.getenv("HA_URL")
    ha_token = os.getenv("HA_TOKEN")
    
    # Optional configuration with defaults
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    default_local_model = os.getenv("DEFAULT_LOCAL_MODEL", "llama3")
    default_cloud_model = os.getenv("DEFAULT_CLOUD_MODEL", "claude-3-opus")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    
    # Validate required configuration
    if not ha_url or not ha_token:
        raise ValueError(
            "HA_URL and HA_TOKEN must be set in environment variables or .env file"
        )
    
    return {
        "ha_url": ha_url,
        "ha_token": ha_token,
        "anthropic_api_key": anthropic_api_key,
        "default_local_model": default_local_model,
        "default_cloud_model": default_cloud_model,
        "ollama_base_url": ollama_base_url
    }


def init_models(config):
    """Initialize models and model switcher"""
    try:
        # Check if MOCK_LOCAL_MODEL is set in environment
        use_mock = os.getenv("MOCK_LOCAL_MODEL", "").lower() in ("true", "1", "yes")
        
        if use_mock:
            logger.info("Using mock model for local model (Ollama not required)")
            # Create a simple mock model using the same LLM class
            from crewai.utilities.mock_llm import MockLLM
            ollama_model = MockLLM()
            anthropic_model = MockLLM()
        else:
            # Initialize model providers
            logger.info("Initializing Ollama model...")
            ollama_model = LLM(
                model=f"ollama/{config['default_local_model']}",
                base_url=config["ollama_base_url"]
            )
            
            # TEMPORARY: Disabled Anthropic model as requested by user for Ollama troubleshooting
            # Initialize both local and cloud with the same Ollama model
            logger.info("Using Ollama for both local and cloud models (Anthropic disabled)")
            anthropic_model = ollama_model
        
        # Initialize model switcher
        model_switcher = ModelSwitcher(
            local_model=ollama_model,
            cloud_model=anthropic_model,
            default_to_local=True
        )
        
        return model_switcher
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        logger.error(
            "If using Ollama, make sure the Ollama server is running. "
            "You can start it by running 'ollama serve' in a terminal."
        )
        if "Cannot assign requested address" in str(e):
            logger.error(
                "Ollama server connection error. Make sure Ollama is running at http://host.docker.internal:11434."
            )
            logger.info("You can set MOCK_LOCAL_MODEL=true in your .env file to use a mock model instead.")
        raise


def init_home_assistant_tool(config):
    """Initialize Home Assistant tool"""
    return HomeAssistantTool(
        base_url=config["ha_url"],
        token=config["ha_token"]
    )


def process_command(args, ha_tool, model_switcher):
    """Process command based on arguments"""
    # Create agents
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
    
    # Process commands
    if args.command == "query":
        # For query command, we use the home_analyzer agent
        task = create_analyze_home_task(
            agent=home_analyzer,
            query=args.text,
            specific_entities=args.entities if args.entities else None
        )
        
        crew = Crew(
            agents=[home_analyzer],
            tasks=[task],
            verbose=True
        )
        
        return crew.kickoff()
        
    elif args.command == "control":
        # For control command, we use both nlp_processor and home_controller
        interpret_task = create_interpret_command_task(
            agent=nlp_processor,
            user_command=args.text
        )
        
        control_task = create_control_lights_task(
            agent=home_controller,
            command=args.text
        )
        
        crew = Crew(
            agents=[nlp_processor, home_controller],
            tasks=[interpret_task, control_task],
            verbose=True
        )
        
        return crew.kickoff()
        
    elif args.command == "discover":
        # For discover command, we use the home_controller agent
        task = create_device_discovery_task(
            agent=home_controller
        )
        
        crew = Crew(
            agents=[home_controller],
            tasks=[task],
            verbose=True
        )
        
        return crew.kickoff()
        
    elif args.command == "automate":
        # For automate command, we use home_analyzer to create automation
        task = create_create_automation_task(
            agent=home_analyzer,
            automation_description=args.description
        )
        
        crew = Crew(
            agents=[home_analyzer],
            tasks=[task],
            verbose=True
        )
        
        return crew.kickoff()
        
    elif args.command == "interpret":
        # For interpret command, we only use nlp_processor
        task = create_interpret_command_task(
            agent=nlp_processor,
            user_command=args.text
        )
        
        crew = Crew(
            agents=[nlp_processor],
            tasks=[task],
            verbose=True
        )
        
        return crew.kickoff()


def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description="Home Assistant Agent - Control smart home with AI agents"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Query command - for querying state
    query_parser = subparsers.add_parser("query", help="Query home state")
    query_parser.add_argument(
        "text", help="Natural language query (e.g., 'what is the temperature in the living room')"
    )
    query_parser.add_argument(
        "--entities", "-e", nargs="+", 
        help="Specific entities to query (comma-separated)"
    )
    
    # Control command - for controlling devices
    control_parser = subparsers.add_parser("control", help="Control devices")
    control_parser.add_argument(
        "text", help="Natural language command (e.g., 'turn on living room lights')"
    )
    
    # Discover command - for discovering devices
    discover_parser = subparsers.add_parser("discover", help="Discover devices")
    
    # Automate command - for creating automations
    automate_parser = subparsers.add_parser("automate", help="Create automation")
    automate_parser.add_argument(
        "description", help="Description of the automation to create"
    )
    
    # Interpret command - for interpreting commands without execution
    interpret_parser = subparsers.add_parser(
        "interpret", help="Interpret natural language command"
    )
    interpret_parser.add_argument(
        "text", help="Natural language command to interpret"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is specified, show help
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize components
        model_switcher = init_models(config)
        ha_tool = init_home_assistant_tool(config)
        
        # Process command
        result = process_command(args, ha_tool, model_switcher)
        
        # Print result
        if result:
            print("\n=== Command Result ===")
            print(result)
    except ValueError as e:
        # Handle configuration errors
        logger.error(f"Configuration error: {str(e)}")
        print(f"\nError: {str(e)}")
        print("\nPlease check your configuration and try again.")
        print("Make sure your .env file contains the necessary variables (HA_URL, HA_TOKEN).")
        sys.exit(1)
    except ConnectionError as e:
        # Handle Home Assistant connection errors
        logger.error(f"Home Assistant connection error: {str(e)}")
        print(f"\nError connecting to Home Assistant: {str(e)}")
        print("\nPlease check your Home Assistant URL and token and try again.")
        print("Make sure your Home Assistant instance is running and accessible.")
        sys.exit(1)
    except Exception as e:
        # Handle other errors
        logger.error(f"Error: {str(e)}")
        if "Cannot assign requested address" in str(e):
            print("\nError: Could not connect to Ollama server.")
            print("You have two options:")
            print("1. Set MOCK_LOCAL_MODEL=true in your .env file to use a mock model")
            print("   This will allow the application to run without Ollama")
            print("   Example: Add 'MOCK_LOCAL_MODEL=true' to your .env file")
            print("\n2. If you want to use Ollama:")
            print("   - Make sure Ollama is installed and running")
            print("   - Start it by running 'ollama serve' in a terminal")
            print("   - If you don't have Ollama installed, please visit https://ollama.ai/")
            print("\nTroubleshooting steps for Ollama:")
            print("1. Check if Ollama is running with: 'ps aux | grep ollama'")
            print("2. Try restarting the Ollama server: 'pkill ollama && ollama serve'")
            print("3. Verify it's listening on host.docker.internal:11434 with: 'curl http://host.docker.internal:11434/api/version'")
            print("4. Ensure no firewall is blocking the connection")
            print("5. If running in Docker, ensure proper network settings and port mappings")
        elif "context window" in str(e).lower() or "prompt is too long" in str(e).lower():
            print("\nError: The request contains too much data for the AI model to process.")
            print("Try one of the following:")
            print("1. Query specific entities using the --entities flag")
            print("2. Use a more specific query")
            print("3. Use a model with a larger context window")
        else:
            print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 