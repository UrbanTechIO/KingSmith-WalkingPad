# number.py
import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, SPEED_MIN, SPEED_MAX, SPEED_STEP

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadSpeedNumber(coordinator)])


class WalkingPadSpeedNumber(NumberEntity):
    """Speed control for the WalkingPad treadmill.
    Shows and sets belt speed in km/h (1.0–12.0, step 0.1).
    Only active while the treadmill is playing.
    """

    _attr_name = "WalkingPad Speed Control"
    _attr_unique_id_suffix = "_speed_control"
    _attr_icon = "mdi:speedometer"
    _attr_native_min_value = SPEED_MIN
    _attr_native_max_value = SPEED_MAX
    _attr_native_step = SPEED_STEP
    _attr_native_unit_of_measurement = "km/h"
    _attr_mode = NumberMode.SLIDER   # renders as a slider with the actual km/h values shown

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.mac}_speed_control"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model=coordinator.model,
        )

    @property
    def native_value(self) -> float:
        """Return current speed from treadmill BLE data."""
        speed = self.coordinator.data.get("speed", SPEED_MIN)
        # Clamp to valid range in case of a 0.0 reading while idle
        return max(SPEED_MIN, min(SPEED_MAX, speed))

    @property
    def available(self) -> bool:
        """Only available when treadmill is actively playing."""
        return (
            self.coordinator.is_connected
            and self.coordinator.data.get("training_status") == "playing"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Called when the user moves the slider or types a value."""
        await self.coordinator.send_set_speed(value)

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_update)

    @callback
    def _handle_update(self):
        self.async_write_ha_state()
