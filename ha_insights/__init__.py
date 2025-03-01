"""HA Insights - Home Assistant pattern analysis and suggestions."""
from __future__ import annotations

import logging
import asyncio
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_STATE_CHANGED
from homeassistant.components.recorder import get_instance

from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_EXCLUDED_ENTITIES,
    CONF_TRACKED_DOMAINS,
    CONF_MIN_STATE_CHANGES,
    CONF_MAX_SUGGESTIONS,
    CONF_PURGE_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MIN_STATE_CHANGES,
    DEFAULT_MAX_SUGGESTIONS,
    DEFAULT_PURGE_DAYS,
    DEFAULT_TRACKED_DOMAINS,
    DEFAULT_INSIGHTS_SCAN_INTERVAL,
    DEFAULT_AGGREGATION_WINDOW,
    EVENT_NEW_INSIGHT,
    SIGNAL_INSIGHTS_UPDATED,
    STORAGE_VERSION,
    STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
                vol.Optional(CONF_EXCLUDED_ENTITIES, default=[]): vol.All(
                    cv.ensure_list, [cv.entity_id]
                ),
                vol.Optional(CONF_TRACKED_DOMAINS, default=DEFAULT_TRACKED_DOMAINS): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_MIN_STATE_CHANGES, default=DEFAULT_MIN_STATE_CHANGES): cv.positive_int,
                vol.Optional(CONF_MAX_SUGGESTIONS, default=DEFAULT_MAX_SUGGESTIONS): cv.positive_int,
                vol.Optional(CONF_PURGE_DAYS, default=DEFAULT_PURGE_DAYS): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the HA Insights integration."""
    hass.data[DOMAIN] = {}
    
    if DOMAIN in config:
        # Not using config from yaml - all config via UI
        _LOGGER.info("HA Insights starting. Configuration will be handled via UI")
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA Insights from a config entry."""
    _LOGGER.info("Setting up HA Insights integration")
    
    # Initialize storage for insights and patterns
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {
        "insights": [],
        "implemented_insights": [],
        "dismissed_insights": [],
        "insight_history": {},
        "last_scan": None,
    }
    
    # Import components
    from .analytics.pattern_observer import PatternObserver
    from .analytics.pattern_analyzer import PatternAnalyzer
    from .analytics.suggestion_generator import SuggestionGenerator
    from .analytics.insight_manager import InsightManager
    
    # Initialize components
    observer = PatternObserver(hass)
    analyzer = PatternAnalyzer(hass)
    suggestion_generator = SuggestionGenerator(hass)
    insight_manager = InsightManager(hass)
    
    # Store components and data
    hass.data[DOMAIN] = {
        "observer": observer,
        "analyzer": analyzer,
        "suggestion_generator": suggestion_generator,
        "insight_manager": insight_manager,
        "store": store,
        "stored_data": stored_data,
    }
    
    # Load insights from storage
    await insight_manager.async_load()
    
    # Configure observer with settings from config entry
    excluded_entities = entry.options.get(CONF_EXCLUDED_ENTITIES, [])
    tracked_domains = entry.options.get(CONF_TRACKED_DOMAINS, DEFAULT_TRACKED_DOMAINS)
    min_state_changes = entry.options.get(CONF_MIN_STATE_CHANGES, DEFAULT_MIN_STATE_CHANGES)
    
    observer.set_excluded_entities(excluded_entities)
    observer.set_tracked_domains(tracked_domains)
    observer.set_min_state_changes(min_state_changes)
    
    # Set up state change listener
    @callback
    def async_handle_state_change(event):
        """Process state changes for pattern detection."""
        entity_id = event.data.get("entity_id")
        if not entity_id:
            return
            
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        if old_state is None or new_state is None:
            return
            
        # Process the state change
        observer.process_state_change(entity_id, old_state, new_state)
    
    # Register state change listener
    hass.bus.async_listen(EVENT_STATE_CHANGED, async_handle_state_change)
    
    # Set up periodic pattern analysis
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    async def async_analyze_patterns(now=None):
        """Run pattern analysis periodically."""
        _LOGGER.debug("Running scheduled pattern analysis")
        
        # Skip if not enough data
        num_entities_tracked = len(observer.get_tracked_entities())
        if num_entities_tracked < 5:  # Arbitrary threshold
            _LOGGER.debug(
                "Not enough entities being tracked for meaningful analysis (%d entities)",
                num_entities_tracked
            )
            return
            
        # Perform analysis
        await analyzer.analyze()
        
        # Log results
        patterns = analyzer.get_patterns()
        _LOGGER.debug("Pattern analysis found %d patterns", len(patterns))
    
    # Register periodic analysis
    async_track_time_interval(
        hass, 
        async_analyze_patterns,
        timedelta(minutes=scan_interval)
    )
    
    # Set up periodic aggregation of state changes
    async def async_aggregate_state_changes(now=None):
        """Aggregate state changes periodically."""
        observer.aggregate_state_changes()
    
    # Register periodic aggregation
    async_track_time_interval(
        hass,
        async_aggregate_state_changes,
        timedelta(minutes=DEFAULT_AGGREGATION_WINDOW)
    )
    
    # Set up periodic purging of old data
    purge_days = entry.options.get(CONF_PURGE_DAYS, DEFAULT_PURGE_DAYS)
    
    async def async_purge_old_insights(now=None):
        """Purge old insights periodically."""
        await insight_manager.async_purge_old_insights(max_age_days=purge_days)
    
    # Register periodic purging
    async_track_time_interval(
        hass,
        async_purge_old_insights,
        timedelta(days=7)  # Weekly purge
    )
    
    # Set up insight scanning
    insight_manager.async_setup_insight_scan()
    
    # Register insight event listener
    insight_manager.async_register_event_listeners()
    
    # Forward entry setup to platforms
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    
    # Register services
    async def async_generate_insights_service(call):
        """Service to generate insights on demand."""
        await suggestion_generator.generate_suggestions()
    
    async def async_dismiss_insight_service(call):
        """Service to dismiss an insight."""
        insight_id = call.data.get("insight_id")
        if not insight_id:
            _LOGGER.error("No insight_id provided to dismiss_insight service")
            return
            
        await insight_manager.async_dismiss_insight(insight_id)
    
    async def async_mark_implemented_service(call):
        """Service to mark an insight as implemented."""
        insight_id = call.data.get("insight_id")
        if not insight_id:
            _LOGGER.error("No insight_id provided to mark_implemented service")
            return
            
        await insight_manager.async_mark_implemented(insight_id)
    
    # Register services
    hass.services.async_register(
        DOMAIN, 
        "generate_insights", 
        async_generate_insights_service
    )
    
    hass.services.async_register(
        DOMAIN,
        "dismiss_insight",
        async_dismiss_insight_service,
        schema=vol.Schema({
            vol.Required("insight_id"): cv.string,
        })
    )
    
    hass.services.async_register(
        DOMAIN,
        "mark_implemented",
        async_mark_implemented_service,
        schema=vol.Schema({
            vol.Required("insight_id"): cv.string,
        })
    )
    
    # Start analysis after Home Assistant is fully started
    @callback
    def async_startup(_):
        """Run first analysis when Home Assistant starts."""
        hass.async_create_task(async_analyze_patterns())
    
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, async_startup)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    # Save insights before unloading
    insight_manager = hass.data[DOMAIN].get("insight_manager")
    if insight_manager:
        await insight_manager.async_save()
    
    # Remove all data
    hass.data.pop(DOMAIN)
    
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)
    
    # Currently no migrations needed as this is the first version
    
    return True 