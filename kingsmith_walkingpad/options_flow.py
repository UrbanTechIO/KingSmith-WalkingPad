import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import CONF_WEIGHT_ENTITY

class WalkingPadOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Show form to pick weight entity (optional)
        schema = vol.Schema({
            vol.Optional(CONF_WEIGHT_ENTITY, default=self.config_entry.options.get(CONF_WEIGHT_ENTITY, "")): selector.EntitySelector(
                selector_type="entity",
                domain="sensor",
                include_disabled=False,
            )
        })
        return self.async_show_form(step_id="init", data_schema=schema)
