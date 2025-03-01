"""Suggestion Generator for creating automation suggestions from patterns."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.template import utcnow
from homeassistant.components.recorder import get_instance

from ..const import (
    DOMAIN,
    EVENT_NEW_INSIGHT,
    CONF_MAX_SUGGESTIONS,
    DEFAULT_MAX_SUGGESTIONS,
    INSIGHT_TYPE_AUTOMATION,
    INSIGHT_TYPE_ENERGY,
    INSIGHT_TYPE_COMFORT,
    INSIGHT_TYPE_CONVENIENCE,
    INSIGHT_TYPE_SECURITY,
)

_LOGGER = logging.getLogger(__name__)


class SuggestionGenerator:
    """
    Generates actionable suggestions from identified patterns.
    
    This class:
    1. Takes patterns from PatternAnalyzer
    2. Converts them into actionable suggestions
    3. Formats automation YAML for users to implement
    4. Prioritizes suggestions by impact and confidence
    """
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the suggestion generator."""
        self.hass = hass
        self._domain = "ha_insights"
        self._max_suggestions = DEFAULT_MAX_SUGGESTIONS
        self._generated_insights: List[Dict[str, Any]] = []
    
    async def generate_suggestions(self) -> List[Dict[str, Any]]:
        """
        Generate actionable suggestions from patterns.
        
        Returns:
            List of suggestion dictionaries
        """
        _LOGGER.debug("Generating suggestions from patterns")
        
        # Get analyzer data
        analyzer = self.hass.data[self._domain].get("analyzer")
        if not analyzer:
            _LOGGER.error("Pattern analyzer not initialized")
            return []
            
        # Get config settings
        entry = self.hass.config_entries.async_entries(self._domain)[0]
        self._max_suggestions = entry.options.get(CONF_MAX_SUGGESTIONS, DEFAULT_MAX_SUGGESTIONS)
        
        # Get patterns
        patterns = analyzer.get_patterns()
        if not patterns:
            _LOGGER.info("No patterns available for generating suggestions")
            return []
        
        # Generate suggestions for different pattern types
        automation_suggestions = await self._generate_automation_suggestions(patterns)
        energy_suggestions = await self._generate_energy_suggestions(patterns)
        comfort_suggestions = await self._generate_comfort_suggestions(patterns)
        
        # Combine all suggestions
        all_suggestions = automation_suggestions + energy_suggestions + comfort_suggestions
        
        # Sort by confidence and limit to max suggestions
        all_suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        suggestions = all_suggestions[:self._max_suggestions]
        
        # Create insights from suggestions
        new_insights = []
        existing_insight_ids = {i["id"] for i in self._generated_insights}
        
        for suggestion in suggestions:
            # Create a unique ID for this insight
            insight_id = f"insight_{suggestion['id']}"
            
            # Skip if already generated
            if insight_id in existing_insight_ids:
                continue
                
            # Create insight
            insight = {
                "id": insight_id,
                "type": suggestion["type"],
                "title": suggestion["title"],
                "description": suggestion["description"],
                "confidence": suggestion["confidence"],
                "entity_id": suggestion.get("entity_id"),
                "related_entity_id": suggestion.get("related_entity_id"),
                "suggestions": [suggestion],
                "timestamp": utcnow().isoformat(),
                "dismissed": False,
            }
            
            # Add to generated insights
            new_insights.append(insight)
            self._generated_insights.append(insight)
            existing_insight_ids.add(insight_id)
            
            # Fire an event for this new insight
            self.hass.bus.async_fire(EVENT_NEW_INSIGHT, insight)
        
        # Update stored data
        if "stored_data" in self.hass.data[self._domain]:
            self.hass.data[self._domain]["stored_data"]["insights"] = self._generated_insights
            await self.hass.data[self._domain]["store"].async_save(
                self.hass.data[self._domain]["stored_data"]
            )
        
        _LOGGER.info("Generated %d new insights from patterns", len(new_insights))
        return new_insights
    
    async def _generate_automation_suggestions(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate automation suggestions from patterns.
        
        Args:
            patterns: List of identified patterns
            
        Returns:
            List of automation suggestion dictionaries
        """
        suggestions = []
        
        # Filter to automation patterns
        automation_patterns = [p for p in patterns if p["type"] == INSIGHT_TYPE_AUTOMATION]
        
        for pattern in automation_patterns:
            entity_id = pattern.get("entity_id")
            if not entity_id:
                continue
                
            domain = entity_id.split(".", 1)[0]
            
            # Handle time-based patterns
            if pattern["id"].startswith("time_pattern_"):
                if "active_hours" in pattern.get("data", {}):
                    active_hours = pattern["data"]["active_hours"]
                    
                    if not active_hours:
                        continue
                        
                    # Create time trigger automation
                    triggers = []
                    for hour in active_hours:
                        triggers.append({
                            "platform": "time",
                            "at": f"{hour:02d}:00:00"
                        })
                    
                    # Generate YAML
                    yaml_content = self._generate_time_automation_yaml(entity_id, domain, triggers)
                    
                    suggestions.append({
                        "id": f"suggestion_{pattern['id']}",
                        "type": INSIGHT_TYPE_AUTOMATION,
                        "entity_id": entity_id,
                        "title": f"Scheduled automation for {entity_id}",
                        "description": f"Automatically control {entity_id} at regular times ({', '.join(f'{h:02d}:00' for h in active_hours)})",
                        "confidence": pattern["confidence"],
                        "yaml": yaml_content,
                        "automation_type": "time_based",
                    })
            
            # Handle correlation patterns
            elif pattern["id"].startswith("correlation_"):
                related_entity_id = pattern.get("related_entity_id")
                if not related_entity_id:
                    continue
                    
                related_domain = related_entity_id.split(".", 1)[0]
                
                # Create state trigger automation
                trigger = {
                    "platform": "state",
                    "entity_id": related_entity_id,
                }
                
                # Add to/from state if we can determine it
                if related_domain == "binary_sensor":
                    trigger["to"] = "on"
                    
                # Generate YAML
                yaml_content = self._generate_state_automation_yaml(entity_id, domain, related_entity_id, trigger)
                
                suggestions.append({
                    "id": f"suggestion_{pattern['id']}",
                    "type": INSIGHT_TYPE_AUTOMATION,
                    "entity_id": entity_id,
                    "related_entity_id": related_entity_id,
                    "title": f"Automation based on {related_entity_id}",
                    "description": f"Automatically control {entity_id} when {related_entity_id} changes state",
                    "confidence": pattern["confidence"],
                    "yaml": yaml_content,
                    "automation_type": "state_based",
                })
        
        return suggestions
    
    async def _generate_energy_suggestions(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate energy-saving suggestions from patterns.
        
        Args:
            patterns: List of identified patterns
            
        Returns:
            List of energy suggestion dictionaries
        """
        suggestions = []
        
        # Filter to energy patterns
        energy_patterns = [p for p in patterns if p["type"] == INSIGHT_TYPE_ENERGY]
        
        for pattern in energy_patterns:
            entity_id = pattern.get("entity_id")
            if not entity_id:
                continue
                
            # For high energy usage patterns
            if pattern["id"].startswith("energy_high_usage_"):
                data = pattern.get("data", {})
                peak_time = data.get("peak_time")
                
                if not peak_time:
                    continue
                    
                # Try to find related entities that might be consuming power
                # This is simplified - in a real implementation, we would use more sophisticated methods
                related_entities = []
                peak_dt = datetime.fromisoformat(peak_time)
                window_start = peak_dt - timedelta(minutes=15)
                window_end = peak_dt + timedelta(minutes=15)
                
                # Find entities that changed state around the peak time
                # This would ideally use the recorder component to query history
                
                suggestions.append({
                    "id": f"suggestion_{pattern['id']}",
                    "type": INSIGHT_TYPE_ENERGY,
                    "entity_id": entity_id,
                    "title": f"Energy optimization for {entity_id}",
                    "description": f"Consider checking devices active around {peak_dt.strftime('%H:%M')} for energy savings",
                    "confidence": pattern["confidence"],
                    "peak_time": peak_time,
                    "potential_savings": "unknown",  # Would calculate in a real implementation
                })
        
        return suggestions
    
    async def _generate_comfort_suggestions(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate comfort improvement suggestions from patterns.
        
        Args:
            patterns: List of identified patterns
            
        Returns:
            List of comfort suggestion dictionaries
        """
        suggestions = []
        
        # Filter to comfort patterns
        comfort_patterns = [p for p in patterns if p["type"] == INSIGHT_TYPE_COMFORT]
        
        for pattern in comfort_patterns:
            entity_id = pattern.get("entity_id")
            if not entity_id:
                continue
                
            # For temperature patterns
            if pattern["id"].startswith("comfort_too_cold_"):
                data = pattern.get("data", {})
                current_temp = data.get("current_temp")
                recommended_min = data.get("recommended_min", 18)
                
                if current_temp is None:
                    continue
                    
                # Find climate entities that could help
                climate_entities = []
                for entity_id in self.hass.states.async_entity_ids("climate"):
                    climate_entities.append(entity_id)
                
                if climate_entities:
                    # Generate YAML for climate adjustment
                    yaml_content = self._generate_climate_adjustment_yaml(
                        climate_entities[0], recommended_min
                    )
                    
                    suggestions.append({
                        "id": f"suggestion_{pattern['id']}",
                        "type": INSIGHT_TYPE_COMFORT,
                        "entity_id": entity_id,
                        "related_entity_id": climate_entities[0] if climate_entities else None,
                        "title": f"Heating suggestion for {entity_id}",
                        "description": f"Increase heating to improve comfort (current: {current_temp:.1f}°C, recommended: at least {recommended_min}°C)",
                        "confidence": pattern["confidence"],
                        "yaml": yaml_content if climate_entities else None,
                        "adjustment": recommended_min - current_temp,
                    })
            
            elif pattern["id"].startswith("comfort_too_warm_"):
                data = pattern.get("data", {})
                current_temp = data.get("current_temp")
                recommended_max = data.get("recommended_max", 25)
                
                if current_temp is None:
                    continue
                    
                # Find climate entities that could help
                climate_entities = []
                for entity_id in self.hass.states.async_entity_ids("climate"):
                    climate_entities.append(entity_id)
                
                if climate_entities:
                    # Generate YAML for climate adjustment
                    yaml_content = self._generate_climate_adjustment_yaml(
                        climate_entities[0], recommended_max
                    )
                    
                    suggestions.append({
                        "id": f"suggestion_{pattern['id']}",
                        "type": INSIGHT_TYPE_COMFORT,
                        "entity_id": entity_id,
                        "related_entity_id": climate_entities[0] if climate_entities else None,
                        "title": f"Cooling suggestion for {entity_id}",
                        "description": f"Increase cooling to improve comfort (current: {current_temp:.1f}°C, recommended: at most {recommended_max}°C)",
                        "confidence": pattern["confidence"],
                        "yaml": yaml_content if climate_entities else None,
                        "adjustment": current_temp - recommended_max,
                    })
        
        return suggestions
    
    def _generate_time_automation_yaml(self, entity_id: str, domain: str, triggers: List[Dict[str, Any]]) -> str:
        """Generate YAML for a time-based automation."""
        yaml_lines = [
            "# Time-based automation for {}".format(entity_id),
            "automation:",
            "  alias: \"Scheduled control for {}\"".format(entity_id),
            "  description: \"Automatically control {} at scheduled times\"".format(entity_id),
            "  trigger:"
        ]
        
        # Add triggers
        for trigger in triggers:
            yaml_lines.append("    - platform: {}".format(trigger["platform"]))
            yaml_lines.append("      at: \"{}\"".format(trigger["at"]))
        
        # Add action based on domain
        yaml_lines.append("  action:")
        
        if domain == "light":
            yaml_lines.append("    - service: light.turn_on")
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
            yaml_lines.append("      data:")
            yaml_lines.append("        brightness_pct: 80")
        elif domain == "switch":
            yaml_lines.append("    - service: switch.turn_on")
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
        elif domain == "climate":
            yaml_lines.append("    - service: climate.set_temperature")
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
            yaml_lines.append("      data:")
            yaml_lines.append("        temperature: 21")
        elif domain == "cover":
            yaml_lines.append("    - service: cover.open_cover")
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
        else:
            # Generic turn_on action
            yaml_lines.append("    - service: {}.turn_on".format(domain))
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
        
        return "\n".join(yaml_lines)
    
    def _generate_state_automation_yaml(
        self,
        entity_id: str,
        domain: str,
        related_entity_id: str,
        trigger: Dict[str, Any]
    ) -> str:
        """Generate YAML for a state-based automation."""
        yaml_lines = [
            "# State-based automation for {} based on {}".format(entity_id, related_entity_id),
            "automation:",
            "  alias: \"Control {} based on {}\"".format(entity_id, related_entity_id),
            "  description: \"Automatically control {} when {} changes state\"".format(entity_id, related_entity_id),
            "  trigger:"
        ]
        
        # Add trigger
        yaml_lines.append("    - platform: {}".format(trigger["platform"]))
        yaml_lines.append("      entity_id: {}".format(trigger["entity_id"]))
        if "to" in trigger:
            yaml_lines.append("      to: \"{}\"".format(trigger["to"]))
        if "from" in trigger:
            yaml_lines.append("      from: \"{}\"".format(trigger["from"]))
        
        # Determine action based on the related entity and domain
        yaml_lines.append("  action:")
        
        related_domain = related_entity_id.split(".", 1)[0]
        
        if related_domain == "binary_sensor" and "motion" in related_entity_id:
            # Motion sensor typically turns on lights
            if domain == "light":
                yaml_lines.append("    - service: light.turn_on")
                yaml_lines.append("      target:")
                yaml_lines.append("        entity_id: {}".format(entity_id))
                yaml_lines.append("      data:")
                yaml_lines.append("        brightness_pct: 80")
            else:
                yaml_lines.append("    - service: {}.turn_on".format(domain))
                yaml_lines.append("      target:")
                yaml_lines.append("        entity_id: {}".format(entity_id))
            
            # Add a delay and turn off condition
            yaml_lines.append("    - delay:")
            yaml_lines.append("        minutes: 5")
            yaml_lines.append("    - condition: state")
            yaml_lines.append("      entity_id: {}".format(related_entity_id))
            yaml_lines.append("      state: \"off\"")
            yaml_lines.append("    - service: {}.turn_off".format(domain))
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
        
        elif related_domain == "binary_sensor" and ("door" in related_entity_id or "window" in related_entity_id):
            # Door/window sensor might control climate or lights
            if domain == "climate":
                yaml_lines.append("    - choose:")
                yaml_lines.append("        - conditions:")
                yaml_lines.append("            - condition: state")
                yaml_lines.append("              entity_id: {}".format(related_entity_id))
                yaml_lines.append("              state: \"on\"")
                yaml_lines.append("          sequence:")
                yaml_lines.append("            - service: climate.set_hvac_mode")
                yaml_lines.append("              target:")
                yaml_lines.append("                entity_id: {}".format(entity_id))
                yaml_lines.append("              data:")
                yaml_lines.append("                hvac_mode: \"off\"")
                yaml_lines.append("        - conditions:")
                yaml_lines.append("            - condition: state")
                yaml_lines.append("              entity_id: {}".format(related_entity_id))
                yaml_lines.append("              state: \"off\"")
                yaml_lines.append("          sequence:")
                yaml_lines.append("            - service: climate.set_hvac_mode")
                yaml_lines.append("              target:")
                yaml_lines.append("                entity_id: {}".format(entity_id))
                yaml_lines.append("              data:")
                yaml_lines.append("                hvac_mode: \"heat_cool\"")
            else:
                # Generic toggle based on state
                yaml_lines.append("    - choose:")
                yaml_lines.append("        - conditions:")
                yaml_lines.append("            - condition: state")
                yaml_lines.append("              entity_id: {}".format(related_entity_id))
                yaml_lines.append("              state: \"on\"")
                yaml_lines.append("          sequence:")
                yaml_lines.append("            - service: {}.turn_on".format(domain))
                yaml_lines.append("              target:")
                yaml_lines.append("                entity_id: {}".format(entity_id))
                yaml_lines.append("        - conditions:")
                yaml_lines.append("            - condition: state")
                yaml_lines.append("              entity_id: {}".format(related_entity_id))
                yaml_lines.append("              state: \"off\"")
                yaml_lines.append("          sequence:")
                yaml_lines.append("            - service: {}.turn_off".format(domain))
                yaml_lines.append("              target:")
                yaml_lines.append("                entity_id: {}".format(entity_id))
        
        elif related_domain in ["person", "device_tracker"]:
            # Presence typically affects lights, climate, etc.
            yaml_lines.append("    - choose:")
            yaml_lines.append("        - conditions:")
            yaml_lines.append("            - condition: state")
            yaml_lines.append("              entity_id: {}".format(related_entity_id))
            yaml_lines.append("              state: \"home\"")
            yaml_lines.append("          sequence:")
            yaml_lines.append("            - service: {}.turn_on".format(domain))
            yaml_lines.append("              target:")
            yaml_lines.append("                entity_id: {}".format(entity_id))
            yaml_lines.append("        - conditions:")
            yaml_lines.append("            - condition: state")
            yaml_lines.append("              entity_id: {}".format(related_entity_id))
            yaml_lines.append("              state: \"not_home\"")
            yaml_lines.append("          sequence:")
            yaml_lines.append("            - service: {}.turn_off".format(domain))
            yaml_lines.append("              target:")
            yaml_lines.append("                entity_id: {}".format(entity_id))
        
        else:
            # Generic control based on state change
            yaml_lines.append("    - service: {}.turn_on".format(domain))
            yaml_lines.append("      target:")
            yaml_lines.append("        entity_id: {}".format(entity_id))
            yaml_lines.append("      data: {}")
        
        return "\n".join(yaml_lines)
    
    def _generate_climate_adjustment_yaml(self, climate_entity: str, target_temp: float) -> str:
        """Generate YAML for a climate adjustment."""
        yaml_lines = [
            "# Climate adjustment for {}".format(climate_entity),
            "automation:",
            "  alias: \"Adjust temperature for {}\"".format(climate_entity),
            "  description: \"Set temperature to improve comfort\"",
            "  trigger:",
            "    - platform: time_pattern",
            "      minutes: \"/30\"",
            "  action:",
            "    - service: climate.set_temperature",
            "      target:",
            "        entity_id: {}".format(climate_entity),
            "      data:",
            "        temperature: {}".format(target_temp)
        ]
        
        return "\n".join(yaml_lines)
    
    def get_insights(self, insight_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get generated insights, optionally filtered by type.
        
        Args:
            insight_type: Optional type to filter by
            
        Returns:
            List of insight dictionaries
        """
        if insight_type:
            return [i for i in self._generated_insights if i["type"] == insight_type]
        return self._generated_insights 