# coordinator.py
import asyncio
import logging
from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import (
    UUID_TREADMILL_DATA,
    UUID_CONTROL_POINT,
    UUID_TREADMILL_STATUS,
    CMD_CONTROL_REQUEST,
    CMD_START,
    CMD_STOP,
    CMD_FINISH,
)

_LOGGER = logging.getLogger(__name__)


class WalkingPadCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name="WalkingPadCoordinator")
        self.mac = (config.get("mac_address") or "").upper()
        self.device_name = config.get("device_name")
        self.client = None
        self.data = {
            "speed": 0.0,
            "distance": 0,
            "energy": 0,
            "elapsed_time": 0,
        }
        self.control_state = None
        self.control_state_last = None
        self._retry_task = None
    
    

    async def async_start(self):
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await asyncio.wait_for(self.async_connect(), timeout=15)
                _LOGGER.info("Connected to WalkingPad on attempt %d", attempt)
                return True
            except asyncio.TimeoutError:
                _LOGGER.warning("Connect attempt %d timed out", attempt)
            except Exception as exc:
                _LOGGER.warning("Connect attempt %d failed: %s", attempt, exc)
            await asyncio.sleep(5)

        _LOGGER.warning("All connect attempts failed; falling back to saved data and scheduling retries.")
        if not self._retry_task or self._retry_task.done():
            self._retry_task = self.hass.loop.create_task(self._retry_loop())
        return False


    async def async_connect(self):
        """Establish BLE connection and subscribe to notifications."""
        if self.is_connected:
            _LOGGER.info("Already connected to WalkingPad")
            return

        _LOGGER.debug("Connecting to WalkingPad at %s", self.mac)
        try:
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if not ble_device:
                raise RuntimeError(f"BLE device {self.mac} not found by HA Bluetooth stack")

            self.client = BleakClient(ble_device)
            await self.client.connect()
        except Exception as exc:
            self.client = None
            _LOGGER.error("Failed to connect to device: %s", exc)
            raise

        try:
            await self.client.start_notify(UUID_TREADMILL_DATA, self._notification_handler)
            await self.client.start_notify(UUID_CONTROL_POINT, self.handle_response)
            await self.client.start_notify(UUID_TREADMILL_STATUS, self._training_status_handler)

            _LOGGER.info("Subscribed to notifications")
        except Exception as exc:
            _LOGGER.error("Failed to subscribe to notifications: %s", exc)

    async def async_stop(self):
        """Disconnect BLE client."""
        await self.disconnect()

    async def disconnect(self):
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                _LOGGER.info("Disconnected from WalkingPad")
            except Exception as exc:
                _LOGGER.debug("Error during disconnect: %s", exc)
        self.client = None

    def _notification_handler(self, sender, data: bytearray):
        """Parse treadmill data notifications."""
        _LOGGER.debug("Received treadmill data notification")
        try:
            speed_raw = int.from_bytes(data[2:4], byteorder="little") / 100
            distance = int.from_bytes(data[4:7], byteorder="little")
            energy = data[7]
            elapsed = int.from_bytes(data[12:14], byteorder="little")
        except Exception as exc:
            _LOGGER.debug("Failed parsing treadmill notification: %s", exc)
            return

        self.data.update({
            "speed": speed_raw,
            "distance": distance,
            "energy": energy,
            "elapsed_time": elapsed,
        })
        try:
            self.async_set_updated_data(self.data)
        except Exception:
            pass

    @property
    def is_connected(self):
        return bool(self.client and self.client.is_connected)

    # Control commands (no changes, just cleaned logs)
    async def send_control_request(self):
        if self.is_connected:
            try:
                await self.client.write_gatt_char(UUID_CONTROL_POINT, CMD_CONTROL_REQUEST, response=True)
            except Exception as e:
                _LOGGER.debug("Error sending CONTROL REQUEST: %s", e)
        else:
            _LOGGER.debug("Cannot send CONTROL REQUEST, client not connected")

    async def send_start(self):
        if self.is_connected:
            await self.send_control_request()
            try:
                await self.client.write_gatt_char(UUID_CONTROL_POINT, CMD_START, response=True)
            except Exception as e:
                _LOGGER.debug("Error sending START: %s", e)
        else:
            _LOGGER.debug("Cannot send START, client not connected")

    async def send_pause(self):
        if self.is_connected:
            await self.send_control_request()
            try:
                await self.client.write_gatt_char(UUID_CONTROL_POINT, CMD_STOP, response=True)
            except Exception as e:
                _LOGGER.debug("Error sending STOP: %s", e)
        else:
            _LOGGER.debug("Cannot send STOP, client not connected")

    async def send_finish(self):
        if self.is_connected:
            await self.send_control_request()
            try:
                await self.client.write_gatt_char(UUID_CONTROL_POINT, CMD_FINISH, response=True)
            except Exception as e:
                _LOGGER.debug("Error sending FINISH: %s", e)
        else:
            _LOGGER.debug("Cannot send FINISH, client not connected")

    def handle_response(self, sender, data):
        """Parse control point responses and update state."""
        _LOGGER.debug("Control point response: %s", " ".join(f"{b:02X}" for b in data))
        try:
            if len(data) >= 2 and data[0] == 0x80:
                opcode = data[1]
                if opcode == 0x07:
                    self.control_state = "playing"
                elif opcode == 0x08:
                    tail = data[2:]
                    if 0x02 in tail:
                        self.control_state = "paused"
                    elif 0x01 in tail:
                        self.control_state = "idle"
                    else:
                        self.control_state = "paused"
                self.control_state_last = self.control_state
        except Exception as exc:
            _LOGGER.debug("Error parsing control response: %s", exc)

        try:
            self.async_set_updated_data(self.data)
        except Exception:
            pass
    
    def _training_status_handler(self, sender, data: bytearray):
        hex_data = " ".join(f"{b:02X}" for b in data)
        _LOGGER.warning(f"Training Status raw data: {hex_data}")

        status_str = "unknown"

        if len(data) >= 2:
            # Check for countdown messages
            if data[0] == 0x03 and len(data) >= 3 and data[1] == 0x0E:
                # Map second byte to countdown number
                countdown_map = {
                    0x33: "countdown 3",
                    0x32: "countdown 2",
                    0x31: "countdown 1",
                }
                status_str = countdown_map.get(data[2], f"mode unknown ({data[2]:02X})")
                if status_str.startswith("countdown"):
                    # Extract the countdown number from the string, e.g. "countdown 3" -> 3
                    countdown_number = int(status_str.split()[1])
            # Playing
            elif data[0] == 0x01 and data[1] == 0x0D:
                status_str = "playing"
            # Stopping / Paused
            elif data[0] == 0x01 and data[1] == 0x0F:
                status_str = "stopping/paused"
            # Idle
            elif data[0] == 0x01 and data[1] == 0x01:
                status_str = "idle"

        _LOGGER.warning(f"Training Status update: {status_str}")

        self.data["training_status_raw"] = status_str
        self.data["countdown_number"] = countdown_number
        # Normalize status for other components
        if "countdown" in status_str:
            self.data["training_status"] = "countdown"
        elif status_str == "playing":
            self.data["training_status"] = "playing"
        elif status_str == "stopping/paused":
            self.data["training_status"] = "paused"
        elif status_str == "idle":
            self.data["training_status"] = "idle"
        else:
            self.data["training_status"] = "unknown"

        try:
            self.async_set_updated_data(self.data)
        except Exception:
            pass

    
    async def _retry_loop(self):
        """Background loop to retry connection until successful."""
        while not self.is_connected:
            _LOGGER.debug("Retry loop: attempting reconnect...")
            try:
                await self.async_connect()
                if self.is_connected:
                    _LOGGER.info("Successfully connected in retry loop")
                    break
            except Exception as e:
                _LOGGER.debug("Retry loop connection failed: %s", e)
            await asyncio.sleep(60)
