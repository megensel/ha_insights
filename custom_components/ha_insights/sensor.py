"""Sensor platform for HA Insights."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Optional, cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    INSIGHT_TYPE_AUTOMATION,
    INSIGHT_TYPE_ENERGY,
    INSIGHT_TYPE_COMFORT,
    INSIGHT_TYPE_CONVENIENCE,
    INSIGHT_TYPE_SECURITY,
    EVENT_NEW_INSIGHT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA Insights sensors."""
    stored_data = hass.data[DOMAIN]["stored_data"]
    insights = stored_data.get("insights", [])
    
    # Create sensor entities for existing insights
    entities = []
    for insight_id, insight in enumerate(insights):
        entities.append(InsightSensor(hass, insight_id, insight))
    
    # Create the summary sensor
    entities.append(InsightSummarySensor(hass, len(insights)))
    
    async_add_entities(entities)
    
    # Create a callback to add new insight sensors when insights are generated
    @callback
    def async_add_insight_sensor(event):
        """Add a new insight sensor when an insight is generated."""
        insight = event.data
        insight_id = len(hass.data[DOMAIN]["stored_data"]["insights"]) - 1
        async_add_entities([InsightSensor(hass, insight_id, insight)])
    
    # Listen for new insight events
    hass.bus.async_listen(EVENT_NEW_INSIGHT, async_add_insight_sensor)


class InsightSensor(SensorEntity):
    """Sensor for a single insight."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:lightbulb-outline"
    
    def __init__(self, hass: HomeAssistant, insight_id: int, insight: dict) -> None:
        """Initialize the insight sensor."""
        self.hass = hass
        self.insight_id = insight_id
        self.insight = insight
        
        insight_type = insight.get("type", "")
        if insight_type == INSIGHT_TYPE_AUTOMATION:
            self._attr_icon = "mdi:robot"
        elif insight_type == INSIGHT_TYPE_ENERGY:
            self._attr_icon = "mdi:flash"
        elif insight_type == INSIGHT_TYPE_COMFORT:
            self._attr_icon = "mdi:sofa"
        elif insight_type == INSIGHT_TYPE_CONVENIENCE:
            self._attr_icon = "mdi:gesture-tap"
        elif insight_type == INSIGHT_TYPE_SECURITY:
            self._attr_icon = "mdi:shield"
        
        self._attr_unique_id = f"insight_{insight_id}"
        self._attr_name = f"Insight {insight_id}"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.insight.get("timestamp")
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "title": self.insight.get("title", ""),
            "description": self.insight.get("description", ""),
            "type": self.insight.get("type", ""),
            "confidence": self.insight.get("confidence", 0),
            "entities": self.insight.get("entities", []),
            "suggestions": self.insight.get("suggestions", []),
            "dismissed": self.insight.get("dismissed", False),
        }


class InsightSummarySensor(SensorEntity):
    """Sensor for showing all insights summary."""
    
    _attr_has_entity_name = True
    _attr_name = "Insights Summary"
    _attr_icon = "mdi:lightbulb-group"
    
    def __init__(self, hass: HomeAssistant, insight_count: int) -> None:
        """Initialize the summary sensor."""
        self.hass = hass
        self._attr_unique_id = "insights_summary"
        self._attr_native_value = insight_count
        
    @property
    def native_value(self) -> StateType:
        """Return the number of insights."""
        if DOMAIN in self.hass.data and "stored_data" in self.hass.data[DOMAIN]:
            return len(self.hass.data[DOMAIN]["stored_data"].get("insights", []))
        return 0
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if DOMAIN in self.hass.data and "stored_data" in self.hass.data[DOMAIN]:
            insights = self.hass.data[DOMAIN]["stored_data"].get("insights", [])
            
            # Count insights by type
            type_counts = {}
            for insight in insights:
                insight_type = insight.get("type", "unknown")
                type_counts[insight_type] = type_counts.get(insight_type, 0) + 1
                
            # Count insights by dismissal status
            dismissed_count = sum(1 for i in insights if i.get("dismissed", False))
            active_count = len(insights) - dismissed_count
            
            # Get the latest insight
            latest_insight = insights[-1] if insights else None
            latest_title = latest_insight.get("title", "") if latest_insight else ""
            
            return {
                "total_insights": len(insights),
                "active_insights": active_count,
                "dismissed_insights": dismissed_count,
                "automation_insights": type_counts.get(INSIGHT_TYPE_AUTOMATION, 0),
                "energy_insights": type_counts.get(INSIGHT_TYPE_ENERGY, 0),
                "comfort_insights": type_counts.get(INSIGHT_TYPE_COMFORT, 0),
                "convenience_insights": type_counts.get(INSIGHT_TYPE_CONVENIENCE, 0),
                "security_insights": type_counts.get(INSIGHT_TYPE_SECURITY, 0),
                "latest_insight": latest_title,
            }
            
        return {
            "total_insights": 0,
            "active_insights": 0,
            "dismissed_insights": 0,
        } 