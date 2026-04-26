import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import (
    DOMAIN,
    CONF_WEIGHT_ENTITY,
    CONF_WATCH_HR_ENTITY,
    CONF_WATCH_STEPS_ENTITY,
    CONF_WATCH_CALORIES_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


class WalkingPadOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for KingSmith WalkingPad."""

    # No __init__ needed — HA 2024.x+ injects self.config_entry automatically

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Strip empty strings — treat them as "not configured"
            cleaned = {k: v for k, v in user_input.items() if v}
            # Push new watch entity config into coordinator immediately (no restart needed)
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            coordinator.load_watch_entities(cleaned)
            return self.async_create_entry(title="", data=cleaned)

        options = self.config_entry.options

        schema = vol.Schema({
            # Weight entity for BMI calculation
            vol.Optional(
                CONF_WEIGHT_ENTITY,
                description={"suggested_value": options.get(CONF_WEIGHT_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
            # Watch — heart rate (live passthrough)
            vol.Optional(
                CONF_WATCH_HR_ENTITY,
                description={"suggested_value": options.get(CONF_WATCH_HR_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
            # Watch — daily steps total (integration computes session delta)
            vol.Optional(
                CONF_WATCH_STEPS_ENTITY,
                description={"suggested_value": options.get(CONF_WATCH_STEPS_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
            # Watch — daily calories total (integration computes session delta)
            vol.Optional(
                CONF_WATCH_CALORIES_ENTITY,
                description={"suggested_value": options.get(CONF_WATCH_CALORIES_ENTITY)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)
