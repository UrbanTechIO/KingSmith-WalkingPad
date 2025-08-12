from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("WalkingPadConnectButton async_setup_entry called")
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadConnectButton(coordinator)])


class WalkingPadConnectButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "WalkingPad Connect"
        self._attr_unique_id = f"{coordinator.mac}_connect"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )

    async def async_press(self):
        """Handle the button press: attempt to connect to the device."""
        if self.coordinator.is_connected:
            _LOGGER.info("Device already connected, no need to connect again.")
            return
        _LOGGER.info("Connect button pressed, attempting connection...")
        try:
            await self.coordinator.async_connect()
            _LOGGER.info("Connection attempt finished.")
        except Exception as e:
            _LOGGER.error("Connection attempt failed: %s", e)
