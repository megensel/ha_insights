"""Insight Manager for storing, retrieving, and managing insights."""
from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import utcnow
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from ..const import (
    DOMAIN,
    SIGNAL_INSIGHTS_UPDATED,
    EVENT_NEW_INSIGHT,
    INSIGHT_TYPE_AUTOMATION,
    INSIGHT_TYPE_ENERGY,
    INSIGHT_TYPE_COMFORT,
    INSIGHT_TYPE_CONVENIENCE,
    INSIGHT_TYPE_SECURITY,
    STORAGE_VERSION,
    STORAGE_KEY,
    DEFAULT_INSIGHTS_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class InsightManager:
    """
    Manages insights storage, retrieval, and lifecycle.
    
    This class:
    1. Stores insights persistently
    2. Provides filtering and sorting capabilities
    3. Handles dismissal and implementation status
    4. Maintains insight history
    """
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the insight manager."""
        self.hass = hass
        self._domain = DOMAIN
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._insights: List[Dict[str, Any]] = []
        self._implemented_insights: List[Dict[str, Any]] = []
        self._dismissed_insights: List[Dict[str, Any]] = []
        self._insight_history: Dict[str, List[Dict[str, Any]]] = {}
        self._last_scan: Optional[datetime] = None
        self._insights_by_entity: Dict[str, List[str]] = {}
    
    async def async_load(self) -> None:
        """Load insights from storage."""
        stored_data = await self._store.async_load()
        
        if stored_data is None:
            stored_data = {
                "insights": [],
                "implemented_insights": [],
                "dismissed_insights": [],
                "insight_history": {},
                "last_scan": None,
            }
        
        self._insights = stored_data.get("insights", [])
        self._implemented_insights = stored_data.get("implemented_insights", [])
        self._dismissed_insights = stored_data.get("dismissed_insights", [])
        self._insight_history = stored_data.get("insight_history", {})
        
        last_scan_str = stored_data.get("last_scan")
        if last_scan_str:
            try:
                self._last_scan = dt_util.parse_datetime(last_scan_str)
            except (ValueError, TypeError):
                self._last_scan = None
        
        # Rebuild entity index
        self._rebuild_entity_index()
        
        _LOGGER.debug(
            "Loaded %d insights, %d implemented, %d dismissed",
            len(self._insights),
            len(self._implemented_insights),
            len(self._dismissed_insights),
        )
    
    def _rebuild_entity_index(self) -> None:
        """Rebuild the entity to insight mapping."""
        self._insights_by_entity = {}
        
        for insight in self._insights:
            entity_id = insight.get("entity_id")
            related_entity_id = insight.get("related_entity_id")
            
            if entity_id:
                if entity_id not in self._insights_by_entity:
                    self._insights_by_entity[entity_id] = []
                self._insights_by_entity[entity_id].append(insight["id"])
            
            if related_entity_id:
                if related_entity_id not in self._insights_by_entity:
                    self._insights_by_entity[related_entity_id] = []
                self._insights_by_entity[related_entity_id].append(insight["id"])
    
    async def async_save(self) -> None:
        """Save insights to storage."""
        await self._store.async_save({
            "insights": self._insights,
            "implemented_insights": self._implemented_insights,
            "dismissed_insights": self._dismissed_insights,
            "insight_history": self._insight_history,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
        })
    
    async def async_add_insight(self, insight: Dict[str, Any]) -> str:
        """
        Add a new insight.
        
        Args:
            insight: The insight to add
            
        Returns:
            The ID of the added insight
        """
        # Ensure the insight has an ID
        if "id" not in insight:
            insight["id"] = f"insight_{uuid.uuid4().hex[:8]}"
        
        # Ensure timestamp is present
        if "timestamp" not in insight:
            insight["timestamp"] = utcnow().isoformat()
        
        # Check if this is a duplicate
        existing_ids = {i["id"] for i in self._insights}
        if insight["id"] in existing_ids:
            # Update existing insight
            for i, existing in enumerate(self._insights):
                if existing["id"] == insight["id"]:
                    # Keep history
                    if existing["id"] not in self._insight_history:
                        self._insight_history[existing["id"]] = []
                    self._insight_history[existing["id"]].append(existing.copy())
                    
                    # Update with new data
                    self._insights[i] = insight
                    break
        else:
            # Add new insight
            self._insights.append(insight)
            
            # Update entity index
            entity_id = insight.get("entity_id")
            related_entity_id = insight.get("related_entity_id")
            
            if entity_id:
                if entity_id not in self._insights_by_entity:
                    self._insights_by_entity[entity_id] = []
                self._insights_by_entity[entity_id].append(insight["id"])
            
            if related_entity_id:
                if related_entity_id not in self._insights_by_entity:
                    self._insights_by_entity[related_entity_id] = []
                self._insights_by_entity[related_entity_id].append(insight["id"])
        
        # Save changes
        await self.async_save()
        
        # Notify listeners
        async_dispatcher_send(self.hass, SIGNAL_INSIGHTS_UPDATED)
        
        return insight["id"]
    
    async def async_add_insights(self, insights: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple insights at once.
        
        Args:
            insights: List of insights to add
            
        Returns:
            List of added insight IDs
        """
        if not insights:
            return []
            
        added_ids = []
        for insight in insights:
            insight_id = await self.async_add_insight(insight)
            added_ids.append(insight_id)
        
        self._last_scan = utcnow()
        await self.async_save()
        
        return added_ids
    
    async def async_dismiss_insight(self, insight_id: str) -> bool:
        """
        Dismiss an insight.
        
        Args:
            insight_id: ID of the insight to dismiss
            
        Returns:
            True if dismissed, False otherwise
        """
        for i, insight in enumerate(self._insights):
            if insight["id"] == insight_id:
                # Mark as dismissed
                insight["dismissed"] = True
                
                # Move to dismissed list
                self._dismissed_insights.append(insight.copy())
                self._insights.pop(i)
                
                # Update entity index
                self._rebuild_entity_index()
                
                # Save changes
                await self.async_save()
                
                # Notify listeners
                async_dispatcher_send(self.hass, SIGNAL_INSIGHTS_UPDATED)
                
                return True
        
        return False
    
    async def async_mark_implemented(self, insight_id: str) -> bool:
        """
        Mark an insight as implemented.
        
        Args:
            insight_id: ID of the insight to mark
            
        Returns:
            True if marked, False otherwise
        """
        for i, insight in enumerate(self._insights):
            if insight["id"] == insight_id:
                # Mark as implemented
                insight["implemented"] = True
                insight["implemented_timestamp"] = utcnow().isoformat()
                
                # Move to implemented list
                self._implemented_insights.append(insight.copy())
                self._insights.pop(i)
                
                # Update entity index
                self._rebuild_entity_index()
                
                # Save changes
                await self.async_save()
                
                # Notify listeners
                async_dispatcher_send(self.hass, SIGNAL_INSIGHTS_UPDATED)
                
                return True
        
        return False
    
    def get_insights(
        self,
        insight_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        dismissed: bool = False,
        implemented: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get insights with optional filtering.
        
        Args:
            insight_type: Optional type to filter by
            entity_id: Optional entity ID to filter by
            dismissed: Whether to include dismissed insights
            implemented: Whether to include implemented insights
            limit: Optional limit of insights to return
            offset: Optional offset for pagination
            
        Returns:
            List of filtered insights
        """
        # Determine which lists to search
        sources = []
        sources.append(self._insights)
        
        if dismissed:
            sources.append(self._dismissed_insights)
            
        if implemented:
            sources.append(self._implemented_insights)
        
        # Filter by entity if requested
        if entity_id and entity_id in self._insights_by_entity:
            insight_ids = set(self._insights_by_entity[entity_id])
            results = []
            
            for source in sources:
                for insight in source:
                    if insight["id"] in insight_ids and (
                        insight_type is None or insight["type"] == insight_type
                    ):
                        results.append(insight)
        else:
            # Filter by type if requested
            if insight_type:
                results = []
                for source in sources:
                    for insight in source:
                        if insight["type"] == insight_type:
                            results.append(insight)
            else:
                # No type filter, combine all sources
                results = []
                for source in sources:
                    results.extend(source)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply pagination
        if offset > 0:
            results = results[offset:]
            
        if limit is not None:
            results = results[:limit]
        
        return results
    
    def get_insight(self, insight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific insight by ID.
        
        Args:
            insight_id: ID of the insight to retrieve
            
        Returns:
            The insight or None if not found
        """
        # Check active insights
        for insight in self._insights:
            if insight["id"] == insight_id:
                return insight
        
        # Check dismissed insights
        for insight in self._dismissed_insights:
            if insight["id"] == insight_id:
                return insight
        
        # Check implemented insights
        for insight in self._implemented_insights:
            if insight["id"] == insight_id:
                return insight
        
        return None
    
    def get_insight_history(self, insight_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of a specific insight.
        
        Args:
            insight_id: ID of the insight
            
        Returns:
            List of historical versions of the insight
        """
        return self._insight_history.get(insight_id, [])
    
    def get_entity_insights(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all insights related to a specific entity.
        
        Args:
            entity_id: Entity ID to get insights for
            
        Returns:
            List of insights for the entity
        """
        if entity_id not in self._insights_by_entity:
            return []
            
        insight_ids = set(self._insights_by_entity[entity_id])
        results = []
        
        # Check active insights
        for insight in self._insights:
            if insight["id"] in insight_ids:
                results.append(insight)
        
        return results
    
    def get_insight_stats(self) -> Dict[str, Any]:
        """
        Get statistics about insights.
        
        Returns:
            Dictionary with insight statistics
        """
        total = len(self._insights) + len(self._dismissed_insights) + len(self._implemented_insights)
        
        # Count by type
        type_counts = {}
        for insight_type in [
            INSIGHT_TYPE_AUTOMATION,
            INSIGHT_TYPE_ENERGY,
            INSIGHT_TYPE_COMFORT,
            INSIGHT_TYPE_CONVENIENCE,
            INSIGHT_TYPE_SECURITY,
        ]:
            type_counts[insight_type] = len(self.get_insights(insight_type=insight_type, dismissed=True, implemented=True))
        
        # Calculate implementation rate
        implementation_rate = 0
        if total > 0:
            implementation_rate = len(self._implemented_insights) / total
        
        return {
            "total": total,
            "active": len(self._insights),
            "dismissed": len(self._dismissed_insights),
            "implemented": len(self._implemented_insights),
            "implementation_rate": implementation_rate,
            "type_counts": type_counts,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
        }
    
    async def async_purge_old_insights(self, max_age_days: int = 30) -> int:
        """
        Purge insights older than the specified age.
        
        Args:
            max_age_days: Maximum age in days to keep
            
        Returns:
            Number of insights purged
        """
        purge_before = utcnow() - timedelta(days=max_age_days)
        purge_before_str = purge_before.isoformat()
        
        # Purge dismissed insights
        original_dismissed_count = len(self._dismissed_insights)
        self._dismissed_insights = [
            insight for insight in self._dismissed_insights
            if insight.get("timestamp", "") > purge_before_str
        ]
        dismissed_purged = original_dismissed_count - len(self._dismissed_insights)
        
        # Purge implemented insights (keep more recent ones)
        original_implemented_count = len(self._implemented_insights)
        self._implemented_insights = [
            insight for insight in self._implemented_insights
            if insight.get("implemented_timestamp", "") > purge_before_str
        ]
        implemented_purged = original_implemented_count - len(self._implemented_insights)
        
        # Remove history older than twice the max age
        old_history_cutoff = utcnow() - timedelta(days=max_age_days * 2)
        old_history_cutoff_str = old_history_cutoff.isoformat()
        
        for insight_id in list(self._insight_history.keys()):
            self._insight_history[insight_id] = [
                version for version in self._insight_history[insight_id]
                if version.get("timestamp", "") > old_history_cutoff_str
            ]
            
            # Remove empty history entries
            if not self._insight_history[insight_id]:
                del self._insight_history[insight_id]
        
        # Save changes
        await self.async_save()
        
        total_purged = dismissed_purged + implemented_purged
        if total_purged > 0:
            _LOGGER.info(
                "Purged %d insights older than %d days (%d dismissed, %d implemented)",
                total_purged,
                max_age_days,
                dismissed_purged,
                implemented_purged,
            )
        
        return total_purged
    
    @callback
    def async_setup_insight_scan(self) -> None:
        """Set up periodic scanning for new insights."""
        # Get settings from config entry
        entry = self.hass.config_entries.async_entries(self._domain)[0]
        scan_interval = entry.options.get("scan_interval", DEFAULT_INSIGHTS_SCAN_INTERVAL)
        
        # Register the handler for insights generation
        async def async_generate_insights_handler(now=None):
            """Generate new insights periodically."""
            _LOGGER.debug("Running scheduled insights scan")
            
            # Get suggestion generator
            suggestion_generator = self.hass.data[self._domain].get("suggestion_generator")
            if not suggestion_generator:
                _LOGGER.error("Suggestion generator not initialized")
                return
                
            # Generate new suggestions
            new_insights = await suggestion_generator.generate_suggestions()
            
            # Add to the insight manager
            if new_insights:
                await self.async_add_insights(new_insights)
        
        # Schedule periodic scan
        self.hass.helpers.event.async_track_time_interval(
            async_generate_insights_handler,
            timedelta(minutes=scan_interval),
        )
        
        # Run initial scan
        self.hass.async_create_task(async_generate_insights_handler())
    
    @callback
    def async_register_event_listeners(self) -> None:
        """Register event listeners for insight management."""
        # Listen for new insights
        @callback
        def async_handle_new_insight(event):
            """Handle new insight events."""
            insight = event.data
            if insight:
                self.hass.async_create_task(self.async_add_insight(insight)) 