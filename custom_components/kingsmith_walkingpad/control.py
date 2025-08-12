# control.py
import logging
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import (
    MediaType,
    MediaPlayerState,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the WalkingPad media player."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadMediaPlayer(coordinator)])


class WalkingPadMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Media player style control for WalkingPad."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
    )

    async def async_connect(self):
        if self.coordinator.is_connected:
            _LOGGER.info("Already connected to device")
            return
        _LOGGER.info("Attempting manual connect to WalkingPad")
        try:
            await self.coordinator.connect()
            _LOGGER.info("Manual connect attempt finished")
        except Exception as e:
            _LOGGER.error("Manual connect failed: %s", e)

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "WalkingPad Control"
        self._attr_unique_id = f"{coordinator.mac}_media"
        self._attr_icon = "mdi:human-scooter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11",
        )
        self._state = MediaPlayerState.IDLE

    @property
    def state(self):
        """Return the current media player state based on training status."""
        training_status = self.coordinator.data.get("training_status")
        countdown_str = self.coordinator.data.get("training_status_raw")

        if training_status == "countdown" and countdown_str:
            # Return the raw countdown string as the state
            # e.g. "countdown 3", "countdown 2"
            return countdown_str

        if training_status == "playing":
            return MediaPlayerState.PLAYING
        elif training_status == "paused":
            return MediaPlayerState.PAUSED
        elif training_status == "idle":
            return MediaPlayerState.IDLE
        else:
            return self._state  # fallback

    async def async_media_play(self):
        """Start the treadmill."""
        if not self.coordinator.is_connected:
            _LOGGER.warning("Cannot play: device not connected")
            return
        await self.coordinator.send_start()
        self._state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self):
        """Pause the treadmill."""
        if not self.coordinator.is_connected:
            _LOGGER.warning("Cannot pause: device not connected")
            return
        await self.coordinator.send_pause()
        self._state = MediaPlayerState.PAUSED
        self.async_write_ha_state()

    async def async_media_stop(self):
        """Stop the treadmill completely."""
        if not self.coordinator.is_connected:
            _LOGGER.warning("Cannot stop: device not connected")
            return
        await self.coordinator.send_finish()
        self._state = MediaPlayerState.IDLE
        self.async_write_ha_state()
