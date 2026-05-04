DOMAIN = "kingsmith_walkingpad"

CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac_address"

# BLE UUIDs
UUID_TREADMILL_DATA = "00002acd-0000-1000-8000-00805f9b34fb"
UUID_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"
UUID_TREADMILL_STATUS = "00002ad3-0000-1000-8000-00805f9b34fb"  # MC11 Training Status
UUID_FITNESS_MACHINE_STATUS = "00002ada-0000-1000-8000-00805f9b34fb"  # MC21 Fitness Machine Status
# UUID_TREADMILL_STATUS = "00002ACC-0000-1000-8000-00805f9b34fb"

MODEL_UUIDS = {
    "WalkingPad MC11": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
        "speed_min": 1.0,
        "speed_max": 12.0,
    },
    "WalkingPad C2": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
        "speed_min": 1.0,
        "speed_max": 6.0,
    },
    "WalkingPad MC21": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_FITNESS_MACHINE_STATUS,  # MC21 uses 2ADA not 2AD3
        "speed_min": 0.5,   # confirmed from 2AD4 Supported Speed Range
        "speed_max": 10.0,  # confirmed from 2AD4 Supported Speed Range
    },
    # Fallback for unknown / future models
    "WalkingPad": {
        "data": UUID_TREADMILL_DATA,
        "control": UUID_CONTROL_POINT,
        "status": UUID_TREADMILL_STATUS,
        "speed_min": 1.0,
        "speed_max": 10.0,
    },
}


# Components
CONF_HEIGHT = "height"
CONF_WEIGHT_ENTITY = "weight_entity"

# Watch integration
CONF_WATCH_HR_ENTITY = "watch_hr_entity"
CONF_WATCH_STEPS_ENTITY = "watch_steps_entity"
CONF_WATCH_CALORIES_ENTITY = "watch_calories_entity"

# Commands — MC11 uses Request Control (0x00) before every command
CMD_CONTROL_REQUEST = bytes([0x00])
CMD_START  = bytes([0x07, 0x01])   # MC11: Start with parameter
CMD_STOP   = bytes([0x08, 0x02])   # MC11: Stop with Pause parameter
CMD_FINISH = bytes([0x08, 0x01])   # MC11: Stop with Stop parameter

# MC21 commands — NO Request Control needed, bare opcodes only
CMD_MC21_START  = bytes([0x07])    # Confirmed from nRF log 18:36:23
CMD_MC21_STOP   = bytes([0x08])    # Confirmed from nRF log 18:37:22

# MC21 proprietary authorization UUID and token
# The KS Fit app writes this static token to unlock 2AD9 control after connecting
# Confirmed from HCI snoop log — identical across 41 sessions
UUID_MC21_AUTH = "d18d2c10-c44c-11e8-a355-529269fb1459"
CMD_MC21_AUTH  = bytes([0x01, 0x00, 0x0D, 0x00, 0x06, 0x0B, 0x0F, 0x0D])

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