#!/usr/bin/env python3
"""Test script for HA Insights integration."""
import asyncio
import aiohttp
import json
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Home Assistant connection settings
HA_URL = "http://localhost:8123"  # Change to your Home Assistant URL
HA_TOKEN = "YOUR_LONG_LIVED_TOKEN"  # Change to your long-lived access token


async def test_integration():
    """Test the HA Insights integration functionality."""
    async with aiohttp.ClientSession() as session:
        # 1. Check if integration is installed and configured
        logger.info("Checking if HA Insights is installed...")
        integration_state = await check_integration(session)
        if not integration_state:
            logger.error("HA Insights integration not found. Please install it first.")
            return False

        # 2. Get insights summary
        logger.info("Getting insights summary...")
        summary = await get_insights_summary(session)
        if not summary:
            logger.warning("No insights summary found. This is normal if the integration was just installed.")
        else:
            logger.info(f"Found {summary.get('total_insights', 0)} insights")

        # 3. Trigger insights generation
        logger.info("Triggering insights generation...")
        if await trigger_insights_generation(session):
            logger.info("Insights generation triggered successfully")
        else:
            logger.error("Failed to trigger insights generation")
            return False

        # 4. Wait for insights to be generated
        logger.info("Waiting for insights to be generated (30 seconds)...")
        await asyncio.sleep(30)

        # 5. Check for new insights
        logger.info("Checking for new insights...")
        new_summary = await get_insights_summary(session)
        if new_summary and new_summary.get('total_insights', 0) > (summary.get('total_insights', 0) if summary else 0):
            logger.info(f"New insights generated! Now have {new_summary.get('total_insights', 0)} insights")
        else:
            logger.warning("No new insights were generated. This may be normal if there's not enough data yet.")

        # 6. Get all insight entities
        logger.info("Getting all insight entities...")
        insights = await get_all_insights(session)
        if insights:
            logger.info(f"Found {len(insights)} insight entities")
            # Display first insight details if available
            if insights:
                first_insight = insights[0]
                logger.info(f"Sample insight: {json.dumps(first_insight, indent=2)}")
        else:
            logger.warning("No insight entities found")

        logger.info("Test completed successfully!")
        return True


async def check_integration(session):
    """Check if HA Insights integration is installed and configured."""
    url = f"{HA_URL}/api/config/config_entries/entry"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            for entry in data:
                if entry.get("domain") == "ha_insights":
                    return entry
        return None


async def get_insights_summary(session):
    """Get the insights summary sensor state."""
    url = f"{HA_URL}/api/states/sensor.insights_summary"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            return data.get("attributes", {})
        return None


async def trigger_insights_generation(session):
    """Trigger the generation of new insights."""
    url = f"{HA_URL}/api/services/ha_insights/generate_insights"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.post(url, headers=headers, json={}) as response:
        return response.status == 200


async def get_all_insights(session):
    """Get all insight entities."""
    url = f"{HA_URL}/api/states"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            insights = [
                {
                    "entity_id": entity["entity_id"],
                    "state": entity["state"],
                    "attributes": entity["attributes"]
                }
                for entity in data
                if entity["entity_id"].startswith("sensor.insight_")
            ]
            return insights
        return []


async def test_sensor_creation(session):
    """Test that sensors are created for new insights."""
    # First get current count of insight sensors
    url = f"{HA_URL}/api/states"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            initial_count = len([
                entity for entity in data
                if entity["entity_id"].startswith("sensor.insight_")
            ])
            logger.info(f"Initial insight sensor count: {initial_count}")

    # Create a test insight
    test_insight = {
        "id": f"test_insight_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "type": "automation",
        "title": "Test Insight",
        "description": "This is a test insight created by the test script",
        "entity_id": "light.living_room",
        "confidence": 90,
        "timestamp": datetime.now().isoformat(),
    }

    # Fire event for new insight
    url = f"{HA_URL}/api/events/ha_insights_new_insight"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with session.post(url, headers=headers, json=test_insight) as response:
        if response.status != 200:
            logger.error("Failed to create test insight")
            return False

    # Wait for sensor to be created
    logger.info("Waiting for sensor creation (5 seconds)...")
    await asyncio.sleep(5)

    # Check if new sensor was created
    async with session.get(f"{HA_URL}/api/states", headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            new_count = len([
                entity for entity in data
                if entity["entity_id"].startswith("sensor.insight_")
            ])
            logger.info(f"New insight sensor count: {new_count}")

            if new_count > initial_count:
                logger.info("✅ Test sensor creation passed!")
                return True
            else:
                logger.error("❌ Test sensor creation failed - no new sensor created")
                return False


if __name__ == "__main__":
    logger.info("Starting HA Insights test script")
    try:
        asyncio.run(test_integration())
    except KeyboardInterrupt:
        logger.info("Test canceled by user")
    except Exception as e:
        logger.error(f"Error during test: {e}")
        sys.exit(1) 