"""Pattern Analyzer for identifying usage patterns in Home Assistant data."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import utcnow
from homeassistant.components.recorder import history

from ..const import (
    INSIGHT_TYPE_AUTOMATION,
    INSIGHT_TYPE_ENERGY,
    INSIGHT_TYPE_COMFORT,
    INSIGHT_TYPE_CONVENIENCE,
    INSIGHT_TYPE_SECURITY,
    INSIGHT_TYPE_ANOMALY,
    CONF_INSIGHT_SENSITIVITY,
    DEFAULT_INSIGHT_SENSITIVITY,
)

_LOGGER = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    Analyzes patterns in Home Assistant usage data.
    
    This class:
    1. Processes entity state patterns to identify regular usage
    2. Finds correlations between entities (e.g., motion sensor -> light)
    3. Detects anomalies in entity behavior
    4. Identifies optimization opportunities (energy, automation, etc.)
    """
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the pattern analyzer."""
        self.hass = hass
        self._domain = "ha_insights"
        self._sensitivity = DEFAULT_INSIGHT_SENSITIVITY
        self._identified_patterns: List[Dict[str, Any]] = []
        self._last_analysis: Optional[datetime] = None
    
    async def analyze(self) -> List[Dict[str, Any]]:
        """
        Run a full analysis to identify patterns and insights.
        
        Returns:
            List of pattern dictionaries
        """
        _LOGGER.debug("Starting pattern analysis")
        
        # Get observer data
        observer = self.hass.data[self._domain].get("observer")
        if not observer:
            _LOGGER.error("Pattern observer not initialized")
            return []
            
        # Get sensitivity setting
        entry = self.hass.config_entries.async_entries(self._domain)[0]
        self._sensitivity = entry.options.get(CONF_INSIGHT_SENSITIVITY, DEFAULT_INSIGHT_SENSITIVITY)
        
        # Analyze time-based patterns
        time_patterns = await self._analyze_time_patterns(observer)
        
        # Analyze entity correlations
        correlation_patterns = await self._analyze_entity_correlations(observer)
        
        # Analyze energy usage patterns
        energy_patterns = await self._analyze_energy_usage()
        
        # Analyze comfort patterns
        comfort_patterns = await self._analyze_comfort_conditions()
        
        # Combine all patterns
        new_patterns = time_patterns + correlation_patterns + energy_patterns + comfort_patterns
        
        # Add to identified patterns, avoiding duplicates
        existing_pattern_ids = {p["id"] for p in self._identified_patterns}
        for pattern in new_patterns:
            if pattern["id"] not in existing_pattern_ids:
                self._identified_patterns.append(pattern)
                existing_pattern_ids.add(pattern["id"])
        
        # Update last analysis timestamp
        self._last_analysis = utcnow()
        
        _LOGGER.info("Pattern analysis complete. Found %d patterns: %d time-based, %d correlations, %d energy, %d comfort",
                   len(new_patterns), len(time_patterns), len(correlation_patterns), 
                   len(energy_patterns), len(comfort_patterns))
        
        return self._identified_patterns
    
    async def _analyze_time_patterns(self, observer) -> List[Dict[str, Any]]:
        """
        Analyze time-based patterns (daily, weekly).
        
        Args:
            observer: Pattern observer instance
            
        Returns:
            List of time-based pattern dictionaries
        """
        patterns = []
        
        # Get daily patterns
        daily_patterns = observer.get_daily_patterns()
        
        # For each entity, look for regular time patterns
        for entity_id, hours in daily_patterns.items():
            domain = entity_id.split(".", 1)[0]
            
            # Skip entities that can't be controlled
            if domain in ["sensor", "binary_sensor", "weather", "sun", "person"]:
                continue
                
            # Look for clear on/off time patterns
            on_hours = []
            for hour, states in hours.items():
                # If entity is turned on significantly more often during this hour
                if states["on"] > states["off"] * 2 and states["on"] >= self._sensitivity:
                    on_hours.append(hour)
            
            # Check if we have a clear pattern
            if len(on_hours) >= 2:
                # Convert hours to readable format
                readable_hours = [f"{h:02d}:00" for h in on_hours]
                
                # Generate pattern ID
                pattern_id = f"time_pattern_{entity_id}_{'_'.join(str(h) for h in on_hours)}"
                
                # Add pattern
                patterns.append({
                    "id": pattern_id,
                    "type": INSIGHT_TYPE_AUTOMATION,
                    "entity_id": entity_id,
                    "title": f"Regular usage pattern for {entity_id}",
                    "description": f"{entity_id} is regularly used around {', '.join(readable_hours)}",
                    "confidence": min(90, 60 + (len(on_hours) * 5)),
                    "data": {
                        "active_hours": on_hours,
                        "days_observed": sum(states["on"] for hour, states in hours.items()),
                    },
                    "timestamp": utcnow().isoformat()
                })
        
        return patterns
    
    async def _analyze_entity_correlations(self, observer) -> List[Dict[str, Any]]:
        """
        Analyze entity correlations to identify relationships.
        
        Args:
            observer: Pattern observer instance
            
        Returns:
            List of correlation pattern dictionaries
        """
        patterns = []
        
        # Get entity correlations
        correlations = observer.get_entity_correlations()
        
        # For each entity, find strong correlations
        for entity_id, related_entities in correlations.items():
            entity_domain = entity_id.split(".", 1)[0]
            
            # Focus on correlations with sensors (most valuable for automation)
            if entity_domain not in ["light", "switch", "climate", "cover", "media_player"]:
                continue
            
            # Find related sensors
            for related_id, score in related_entities.items():
                related_domain = related_id.split(".", 1)[0]
                
                # Only consider strong correlations with sensors
                if score < 0.5 or related_domain not in ["binary_sensor", "sensor", "person", "device_tracker"]:
                    continue
                
                # Generate pattern ID
                pattern_id = f"correlation_{entity_id}_{related_id}"
                
                # Create correlation description
                description = f"{entity_id} appears to be controlled based on {related_id}"
                
                if related_domain == "binary_sensor":
                    if "motion" in related_id or "presence" in related_id or "occupancy" in related_id:
                        description = f"{entity_id} turns on when motion is detected by {related_id}"
                    elif "door" in related_id or "window" in related_id:
                        description = f"{entity_id} changes when {related_id} is opened or closed"
                elif related_domain == "person" or related_domain == "device_tracker":
                    description = f"{entity_id} changes when {related_id} arrives or leaves"
                
                # Add pattern
                patterns.append({
                    "id": pattern_id,
                    "type": INSIGHT_TYPE_AUTOMATION,
                    "entity_id": entity_id,
                    "related_entity_id": related_id,
                    "title": f"Relationship between {entity_id} and {related_id}",
                    "description": description,
                    "confidence": int(score * 100),
                    "data": {
                        "correlation_score": score,
                    },
                    "timestamp": utcnow().isoformat()
                })
        
        return patterns
    
    async def _analyze_energy_usage(self) -> List[Dict[str, Any]]:
        """
        Analyze energy usage patterns to find optimization opportunities.
        
        Returns:
            List of energy pattern dictionaries
        """
        patterns = []
        
        # Get entity states
        energy_entities = []
        for entity_id in self.hass.states.async_entity_ids():
            # Look for energy-related sensors
            if entity_id.startswith("sensor.") and any(
                keyword in entity_id for keyword in ["power", "energy", "electricity", "consumption", "usage"]
            ):
                energy_entities.append(entity_id)
        
        if not energy_entities:
            return patterns
        
        # Get history for energy entities
        end_time = utcnow()
        start_time = end_time - timedelta(days=7)
        energy_history = await history.get_significant_states(
            self.hass, start_time, end_time, energy_entities
        )
        
        # Analyze each energy entity
        for entity_id, states in energy_history.items():
            if not states:
                continue
                
            # Convert states to numeric values
            try:
                values = []
                timestamps = []
                for state in states:
                    try:
                        val = float(state.state)
                        values.append(val)
                        timestamps.append(state.last_updated)
                    except (ValueError, TypeError):
                        continue
                
                if not values:
                    continue
                    
                # Simple analysis - look for high usage periods
                mean_value = sum(values) / len(values)
                max_value = max(values)
                
                # If max is significantly higher than mean, might indicate inefficiency
                if max_value > mean_value * 3 and mean_value > 0:
                    # Find when max occurred
                    max_idx = values.index(max_value)
                    max_time = timestamps[max_idx]
                    
                    # Generate pattern ID
                    pattern_id = f"energy_high_usage_{entity_id}"
                    
                    # Add pattern
                    patterns.append({
                        "id": pattern_id,
                        "type": INSIGHT_TYPE_ENERGY,
                        "entity_id": entity_id,
                        "title": f"High energy usage detected for {entity_id}",
                        "description": f"Energy usage for {entity_id} peaked at {max_value:.1f} on {max_time.strftime('%Y-%m-%d %H:%M')}",
                        "confidence": 75,
                        "data": {
                            "average_usage": mean_value,
                            "peak_usage": max_value,
                            "peak_time": max_time.isoformat(),
                        },
                        "timestamp": utcnow().isoformat()
                    })
            except Exception as e:
                _LOGGER.error("Error analyzing energy entity %s: %s", entity_id, str(e))
        
        return patterns
    
    async def _analyze_comfort_conditions(self) -> List[Dict[str, Any]]:
        """
        Analyze comfort conditions (temperature, humidity) for optimization.
        
        Returns:
            List of comfort pattern dictionaries
        """
        patterns = []
        
        # Find climate devices and temperature sensors
        climate_entities = []
        temp_sensors = []
        
        for entity_id in self.hass.states.async_entity_ids():
            if entity_id.startswith("climate."):
                climate_entities.append(entity_id)
            elif entity_id.startswith("sensor.") and any(
                keyword in entity_id for keyword in ["temp", "temperature"]
            ):
                temp_sensors.append(entity_id)
        
        if not climate_entities and not temp_sensors:
            return patterns
        
        # Analyze temperature conditions
        for entity_id in temp_sensors:
            state = self.hass.states.get(entity_id)
            if not state:
                continue
                
            try:
                temp = float(state.state)
                
                # Check for uncomfortable temperatures
                if temp < 18:  # Too cold
                    pattern_id = f"comfort_too_cold_{entity_id}"
                    patterns.append({
                        "id": pattern_id,
                        "type": INSIGHT_TYPE_COMFORT,
                        "entity_id": entity_id,
                        "title": f"Low temperature detected by {entity_id}",
                        "description": f"Temperature is {temp:.1f}°C, which might be too cold for comfort",
                        "confidence": min(90, 60 + int((18 - temp) * 5)),
                        "data": {
                            "current_temp": temp,
                            "recommended_min": 18,
                        },
                        "timestamp": utcnow().isoformat()
                    })
                elif temp > 25:  # Too warm
                    pattern_id = f"comfort_too_warm_{entity_id}"
                    patterns.append({
                        "id": pattern_id,
                        "type": INSIGHT_TYPE_COMFORT,
                        "entity_id": entity_id,
                        "title": f"High temperature detected by {entity_id}",
                        "description": f"Temperature is {temp:.1f}°C, which might be too warm for comfort",
                        "confidence": min(90, 60 + int((temp - 25) * 5)),
                        "data": {
                            "current_temp": temp,
                            "recommended_max": 25,
                        },
                        "timestamp": utcnow().isoformat()
                    })
            except (ValueError, TypeError):
                continue
        
        return patterns
    
    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get identified patterns, optionally filtered by type.
        
        Args:
            pattern_type: Optional type to filter by
            
        Returns:
            List of pattern dictionaries
        """
        if pattern_type:
            return [p for p in self._identified_patterns if p["type"] == pattern_type]
        return self._identified_patterns 