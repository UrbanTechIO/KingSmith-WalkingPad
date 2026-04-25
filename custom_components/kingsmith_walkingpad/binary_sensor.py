# binary_sensor.py
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadConnectedSensor(coordinator)])


class WalkingPadConnectedSensor(BinarySensorEntity):
    """Shows whether the WalkingPad BLE connection is active."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "WalkingPad Connected"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.mac}_connected"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model=coordinator.model,
        )

    @property
    def is_on(self) -> bool:
        """True = Connected, False = Disconnected."""
        return self.coordinator.is_connected

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_update)

    @callback
    def _handle_update(self):
        self.async_write_ha_state()