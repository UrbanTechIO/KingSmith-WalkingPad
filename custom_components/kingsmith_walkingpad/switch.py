# switch.py
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_WATCH_STEPS_ENTITY, CONF_WATCH_CALORIES_ENTITY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadUseWatchSwitch(coordinator, entry)])


class WalkingPadUseWatchSwitch(SwitchEntity):
    """Switch that toggles between treadmill data and watch data for Steps and Energy sensors."""

    _attr_name = "WalkingPad Use Watch"
    _attr_icon = "mdi:watch"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{coordinator.mac}_use_watch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model=coordinator.model,
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.use_watch

    @property
    def available(self) -> bool:
        """Only available when at least one watch entity (steps or calories) is configured."""
        options = self._entry.options
        data = self._entry.data
        has_steps = options.get(CONF_WATCH_STEPS_ENTITY) or data.get(CONF_WATCH_STEPS_ENTITY)
        has_calories = options.get(CONF_WATCH_CALORIES_ENTITY) or data.get(CONF_WATCH_CALORIES_ENTITY)
        return bool(has_steps or has_calories)

    async def async_turn_on(self, **kwargs):
        """Enable watch data mode."""
        _LOGGER.info("Watch mode enabled")
        self.coordinator.use_watch = True
        # If treadmill is currently playing, start a fresh session snapshot immediately
        if self.coordinator.data.get("training_status") == "playing":
            self.coordinator.start_watch_session()
        self.coordinator.update_watch_data()
        try:
            self.coordinator.async_set_updated_data(self.coordinator.data)
        except Exception:
            pass
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Disable watch mode, revert to treadmill data."""
        _LOGGER.info("Watch mode disabled — reverting to treadmill data")
        self.coordinator.use_watch = False
        self.coordinator.reset_watch_session()
        try:
            self.coordinator.async_set_updated_data(self.coordinator.data)
        except Exception:
            pass
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_update)

    @callback
    def _handle_update(self):
        self.async_write_ha_state()
