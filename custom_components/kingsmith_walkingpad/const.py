DOMAIN = "kingsmith_walkingpad"

CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac_address"

# BLE UUIDs
UUID_TREADMILL_DATA = "00002acd-0000-1000-8000-00805f9b34fb"
UUID_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"
UUID_TREADMILL_STATUS = "00002ad3-0000-1000-8000-00805f9b34fb"
# UUID_TREADMILL_STATUS = "00002ACC-0000-1000-8000-00805f9b34fb"

MODEL_UUIDS = {
    "WalkingPad MC11": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
    },
    "WalkingPad C2": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
    },
    # Fallback for unknown / future models
    "WalkingPad": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
    },
}


# Components
CONF_HEIGHT = "height"
CONF_WEIGHT_ENTITY = "weight_entity"

# Watch integration
CONF_WATCH_HR_ENTITY = "watch_hr_entity"
CONF_WATCH_STEPS_ENTITY = "watch_steps_entity"
CONF_WATCH_CALORIES_ENTITY = "watch_calories_entity"

# Commands
CMD_CONTROL_REQUEST = bytes([0x00])
CMD_START = bytes([0x07, 0x01])
CMD_STOP = bytes([0x08, 0x02])
CMD_FINISH = bytes([0x08, 0x01])

# Speed control
SPEED_MIN = 1.0   # km/h
SPEED_MAX = 12.0  # km/h
SPEED_STEP = 0.1  # km/h resolution the treadmill accepts

def cmd_set_speed(kmh: float) -> bytes:
    """Build a Set Target Speed FTMS command.
    Opcode 0x02, speed = km/h * 100 as little-endian uint16.
    E.g. 6.0 km/h → [0x02, 0x58, 0x02]
    """
    value = int(round(kmh * 100))
    return bytes([0x02]) + value.to_bytes(2, "little")