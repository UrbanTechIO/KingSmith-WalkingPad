import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from .const import DOMAIN
from .coordinator import WalkingPadCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "media_player", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("WalkingPad: async_setup_entry called for %s", entry.data)
    coordinator = WalkingPadCoordinator(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def _start_callback(_):
        _LOGGER.info("WalkingPad: Starting coordinator connection attempts")
        await coordinator.async_start()

    # Wait until HA fully started to start connection attempts
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _start_callback)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
