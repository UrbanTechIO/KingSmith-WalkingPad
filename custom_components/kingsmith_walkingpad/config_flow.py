import logging
import voluptuous as vol
import homeassistant
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN, CONF_DEVICE_NAME, CONF_MAC, CONF_HEIGHT, CONF_WEIGHT_ENTITY
from bleak import BleakScanner
from .options_flow import WalkingPadOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

import inspect
_LOGGER.debug(f"EntitySelector __init__ signature: {inspect.signature(selector.EntitySelector.__init__)}")

SUPPORTED_NAME_PREFIXES = (
    "KS-AP",     # MC11
    "KS-C2",     # C2
    "KS-",       # future Kingsmith
    "WalkingPad"
)

def normalize_model(ble_name: str) -> str:
    """Normalize BLE name into a stable WalkingPad model."""
    if not ble_name:
        return "WalkingPad"

    if ble_name.startswith("KS-C2"):
        return "WalkingPad C2"
    if ble_name.startswith("KS-AP"):
        return "WalkingPad MC11"
    if ble_name.startswith("KS-"):
        return "WalkingPad"

    return "WalkingPad"


class WalkingPadConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial step for setting up integration."""
        errors = {}

        # If we have user input (from any form), create the entry
        # if user_input is not None:
        #     return self.async_create_entry(
        #         title=user_input[CONF_DEVICE_NAME],
        #         data=user_input
        #     )

        # Try scanning for KS-AP devices
        _LOGGER.debug("Scanning for WalkingPad BLE devices...")
        devices = await BleakScanner.discover(timeout=10.0)
        ks_devices = [d for d in devices if d.name and d.name.startswith(SUPPORTED_NAME_PREFIXES)]

        if ks_devices:
            # If we found at least one device, pick the first (or you could build a dropdown if multiple)
            dev = ks_devices[0]
            _LOGGER.info("Found WalkingPad device: %s [%s]", dev.name, dev.address)

            self.context["detected_mac"] = dev.address
            # self.context["detected_model"] = dev.name
            self.context["detected_model"] = normalize_model(dev.name)


            # Ask user for friendly name only, store MAC automatically
            schema = vol.Schema({
                vol.Required(CONF_DEVICE_NAME, default=dev.name): str,
                vol.Optional(CONF_HEIGHT): vol.All(vol.Coerce(float), vol.Range(min=50, max=250)),
                vol.Optional(CONF_WEIGHT_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"],
                        device_class="weight"
                    )
                ),
            })

            # Temporarily store MAC in context so we can use it when they submit
            return self.async_show_form(step_id="confirm_name", data_schema=schema, errors=errors)
        
        return await self.async_step_manual()

        # # Fallback — no devices found, ask for full details
        # schema = vol.Schema({
        #     vol.Required(CONF_DEVICE_NAME): str,
        #     vol.Required(CONF_MAC): str,
        #     vol.Required(CONF_HEIGHT): vol.All(vol.Coerce(float), vol.Range(min=50, max=250)),
        #     vol.Optional(CONF_WEIGHT_ENTITY): selector.EntitySelector(
        #         selector.EntitySelectorConfig(
        #             domain=["sensor"],
        #             device_class="weight"
        #         )
        #     ),
        # })
        # return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    async def async_step_confirm_name(self, user_input=None):
        """Step where user confirms/fills device name after auto-discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data={
                    CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                    CONF_MAC: self.context["detected_mac"],
                    "model": self.context.get("detected_model", "unknown"),
                    CONF_HEIGHT: user_input[CONF_HEIGHT],
                    CONF_WEIGHT_ENTITY: user_input.get(CONF_WEIGHT_ENTITY)
                }
            )

        # In case something went wrong, fallback to manual entry
        schema = vol.Schema({
            vol.Required(CONF_DEVICE_NAME): str,
            vol.Required(CONF_HEIGHT): vol.All(vol.Coerce(float), vol.Range(min=50, max=250)),
            vol.Optional(CONF_WEIGHT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor"],
                    device_class="weight"
                )
            ),
        })
        return self.async_show_form(step_id="confirm_name", data_schema=schema)

    async def async_step_manual(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data=user_input,
            )

        schema = vol.Schema({
            vol.Required(CONF_DEVICE_NAME): str,
            vol.Required(CONF_MAC): str,
            # vol.Optional("model", default="unknown"): str,
            vol.Optional("model", default="WalkingPad"): str,
            vol.Optional(CONF_HEIGHT): vol.All(
                vol.Coerce(float), vol.Range(min=50, max=250)
            ),
            vol.Optional(CONF_WEIGHT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor"],
                    device_class="weight",
                )
            ),
        })

        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
        )


    def async_get_options_flow(self):
        return WalkingPadOptionsFlowHandler(self.config_entry)