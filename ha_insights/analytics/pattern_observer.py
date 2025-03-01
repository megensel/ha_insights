"""Pattern Observer for monitoring Home Assistant entity changes."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.template import utcnow
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Time window for aggregating state changes (to avoid processing every small change)
DEFAULT_AGGREGATION_WINDOW = timedelta(minutes=10)

# Number of state changes to keep in history
MAX_STATE_CHANGES = 1000


class PatternObserver:
    """
    Monitors state changes in Home Assistant and identifies patterns.
    
    This class:
    1. Observes entity state changes
    2. Records usage patterns (time of day, day of week, etc.)
    3. Identifies relationships between entities
    4. Maintains a history of state changes for analysis
    """
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the pattern observer."""
        self.hass = hass
        self._domains_to_track: List[str] = []
        self._exclude_entities: Set[str] = set()
        
        # Storage for observations
        self._state_changes: Dict[str, List[Dict[str, Any]]] = {}
        self._daily_patterns: Dict[str, Dict[int, Dict[str, int]]] = {}
        self._weekly_patterns: Dict[str, Dict[int, Dict[str, int]]] = {}
        self._entity_correlations: Dict[str, Dict[str, float]] = {}
        
        # Aggregated state tracking (to avoid processing too many changes)
        self._pending_changes: Dict[str, List[Dict[str, Any]]] = {}
        self._last_aggregation: datetime = utcnow()
        
        # Schedule regular aggregation
        async_track_point_in_time(
            hass,
            self._aggregate_state_changes,
            dt_util.utcnow() + DEFAULT_AGGREGATION_WINDOW
        )
    
    def set_tracked_domains(self, domains: List[str]) -> None:
        """Set the domains to track for pattern analysis."""
        self._domains_to_track = domains
    
    def exclude_entities(self, entity_ids: List[str]) -> None:
        """Exclude specific entities from tracking."""
        self._exclude_entities.update(entity_ids)
    
    def get_tracked_entities(self) -> Set[str]:
        """Get the list of entities being tracked."""
        entities = set()
        
        # If specific domains are set, track all entities in those domains
        if self._domains_to_track:
            for entity_id in self.hass.states.async_entity_ids():
                domain = entity_id.split(".", 1)[0]
                if domain in self._domains_to_track and entity_id not in self._exclude_entities:
                    entities.add(entity_id)
        else:
            # If no domains specified, track all entities except excluded ones
            entities = set(self.hass.states.async_entity_ids()) - self._exclude_entities
        
        return entities
    
    def process_state_change(self, entity_id: str, old_state: State, new_state: State) -> None:
        """Process a state change event and record relevant information."""
        # Skip if entity should be excluded
        if entity_id in self._exclude_entities:
            return
        
        # Skip if domain not in tracked domains (if domains are specified)
        if self._domains_to_track:
            domain = entity_id.split(".", 1)[0]
            if domain not in self._domains_to_track:
                return
        
        # Skip if state hasn't actually changed
        if old_state.state == new_state.state:
            # For some entities, attributes changes might be significant
            # (e.g., light brightness, climate temperature)
            domain = entity_id.split(".", 1)[0]
            significant_attribute_change = False
            
            if domain == "light" and "brightness" in old_state.attributes and "brightness" in new_state.attributes:
                old_brightness = old_state.attributes["brightness"]
                new_brightness = new_state.attributes["brightness"]
                if abs(old_brightness - new_brightness) > 20:  # Significant brightness change
                    significant_attribute_change = True
            
            if domain == "climate" and "temperature" in old_state.attributes and "temperature" in new_state.attributes:
                old_temp = old_state.attributes["temperature"]
                new_temp = new_state.attributes["temperature"]
                if abs(old_temp - new_temp) > 1.0:  # Significant temperature change
                    significant_attribute_change = True
            
            if not significant_attribute_change:
                return
        
        # Record the state change
        now = utcnow()
        
        change = {
            "entity_id": entity_id,
            "old_state": old_state.state,
            "new_state": new_state.state,
            "old_attributes": dict(old_state.attributes),
            "new_attributes": dict(new_state.attributes),
            "timestamp": now.isoformat(),
            "time_of_day": now.hour,
            "day_of_week": now.weekday(),
            "date": now.date().isoformat(),
        }
        
        # Add to pending changes for later aggregation
        if entity_id not in self._pending_changes:
            self._pending_changes[entity_id] = []
        
        self._pending_changes[entity_id].append(change)
        
        # If we have too many pending changes, process them now
        if sum(len(changes) for changes in self._pending_changes.values()) > 100:
            self._process_pending_changes()
    
    async def _aggregate_state_changes(self, _now: datetime) -> None:
        """Aggregate state changes periodically."""
        self._process_pending_changes()
        
        # Schedule the next aggregation
        async_track_point_in_time(
            self.hass,
            self._aggregate_state_changes,
            dt_util.utcnow() + DEFAULT_AGGREGATION_WINDOW
        )
    
    def _process_pending_changes(self) -> None:
        """Process pending state changes and update patterns."""
        if not self._pending_changes:
            return
        
        for entity_id, changes in self._pending_changes.items():
            if not changes:
                continue
                
            # Initialize storage for this entity if needed
            if entity_id not in self._state_changes:
                self._state_changes[entity_id] = []
                
            if entity_id not in self._daily_patterns:
                self._daily_patterns[entity_id] = {hour: {"on": 0, "off": 0, "other": 0} for hour in range(24)}
                
            if entity_id not in self._weekly_patterns:
                self._weekly_patterns[entity_id] = {day: {"on": 0, "off": 0, "other": 0} for day in range(7)}
            
            # Process each change
            for change in changes:
                # Add to state history, keeping only the most recent changes
                self._state_changes[entity_id].append(change)
                if len(self._state_changes[entity_id]) > MAX_STATE_CHANGES:
                    self._state_changes[entity_id].pop(0)
                
                # Update daily patterns
                hour = change["time_of_day"]
                state = self._classify_state(change["new_state"])
                self._daily_patterns[entity_id][hour][state] += 1
                
                # Update weekly patterns
                day = change["day_of_week"]
                self._weekly_patterns[entity_id][day][state] += 1
        
        # Look for entity correlations in recently changed entities
        changed_entities = list(self._pending_changes.keys())
        if len(changed_entities) > 1:
            self._update_entity_correlations(changed_entities)
        
        # Clear pending changes
        self._pending_changes = {}
        self._last_aggregation = utcnow()
        
        _LOGGER.debug("Processed %d state changes for %d entities", 
                     sum(len(changes) for changes in self._pending_changes.values()),
                     len(self._pending_changes))
    
    def _classify_state(self, state: str) -> str:
        """Classify a state value as on, off, or other."""
        if state.lower() in ("on", "home", "open", "unlocked", "active", "playing"):
            return "on"
        elif state.lower() in ("off", "away", "closed", "locked", "inactive", "idle", "paused", "standby"):
            return "off"
        else:
            return "other"
    
    def _update_entity_correlations(self, entities: List[str]) -> None:
        """Update the correlation scores between entities that changed together."""
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Skip self-correlations
                if entity1 == entity2:
                    continue
                
                # Initialize correlation entry if needed
                if entity1 not in self._entity_correlations:
                    self._entity_correlations[entity1] = {}
                if entity2 not in self._entity_correlations:
                    self._entity_correlations[entity2] = {}
                
                # Increase correlation score for these entities
                # (entities that change at similar times are likely related)
                if entity2 not in self._entity_correlations[entity1]:
                    self._entity_correlations[entity1][entity2] = 0.1
                else:
                    # Increase correlation score, but cap at 0.9 (never assume perfect correlation)
                    self._entity_correlations[entity1][entity2] = min(
                        0.9, self._entity_correlations[entity1][entity2] + 0.05
                    )
                
                # Correlation works both ways
                if entity1 not in self._entity_correlations[entity2]:
                    self._entity_correlations[entity2][entity1] = 0.1
                else:
                    self._entity_correlations[entity2][entity1] = min(
                        0.9, self._entity_correlations[entity2][entity1] + 0.05
                    )
    
    def get_state_changes(self, entity_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get the recorded state changes."""
        if entity_id:
            return {entity_id: self._state_changes.get(entity_id, [])}
        return self._state_changes
    
    def get_daily_patterns(self, entity_id: Optional[str] = None) -> Dict[str, Dict[int, Dict[str, int]]]:
        """Get the daily usage patterns (by hour of day)."""
        if entity_id:
            return {entity_id: self._daily_patterns.get(entity_id, {})}
        return self._daily_patterns
    
    def get_weekly_patterns(self, entity_id: Optional[str] = None) -> Dict[str, Dict[int, Dict[str, int]]]:
        """Get the weekly usage patterns (by day of week)."""
        if entity_id:
            return {entity_id: self._weekly_patterns.get(entity_id, {})}
        return self._weekly_patterns
    
    def get_entity_correlations(self, entity_id: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Get the entity correlation scores."""
        if entity_id:
            return {entity_id: self._entity_correlations.get(entity_id, {})}
        return self._entity_correlations 