import math
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, RestoreEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change

from .const import DOMAIN, CONF_HEIGHT, CONF_WEIGHT_ENTITY

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    raw_height = entry.data.get(CONF_HEIGHT)
    height = float(raw_height) / 100 if raw_height else None
    weight_entity_id = entry.data.get(CONF_WEIGHT_ENTITY)

    tracker = WalkingPadEnergyTracker(hass, coordinator.mac, coordinator.async_set_updated_data)


    sensors = [
        WalkingPadSensor(coordinator, "speed", "Speed", "km/h", "mdi:run"),
        WalkingPadSensor(coordinator, "distance", "Distance", "m", "mdi:map-marker-distance"),
        WalkingPadSensor(coordinator, "energy", "Energy", "kcal", "mdi:fire"),  # raw energy from device
        WalkingPadStepsSensor(coordinator, "steps", "Steps", "steps"),
        WalkingPadEnergyAggregateSensor(coordinator, tracker, "daily", "Daily Energy"),
        WalkingPadEnergyAggregateSensor(coordinator, tracker, "weekly", "Weekly Energy"),
        WalkingPadEnergyAggregateSensor(coordinator, tracker, "monthly", "Monthly Energy"),
        WalkingPadEnergyAggregateSensor(coordinator, tracker, "total", "Total Energy"),
    ]
    if height:
        bmi_sensor = WalkingPadBmiSensor(coordinator, height, weight_entity_id)
        sensors.append(bmi_sensor)
        sensors.append(WalkingPadBmiRatingSensor(coordinator, bmi_sensor))

    sensors.append(WalkingPadElapsedTimeSensor(coordinator))
    async_add_entities(sensors)


STEP_LENGTH_METERS = 0.7  # average adult walking step length in meters


class WalkingPadElapsedTimeSensor(SensorEntity):
    """Sensor to display elapsed time as HH:MM:SS."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "WalkingPad Elapsed Time"
        self._attr_unique_id = f"{coordinator.mac}_elapsed_time_formatted"
        self._attr_native_unit_of_measurement = None
        self._attr_icon = "mdi:timer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )

    @property
    def native_value(self):
        seconds = self.coordinator.data.get("elapsed_time", 0)
        if seconds is None:
            return None
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{secs:02}"

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()


class WalkingPadBmiSensor(SensorEntity):
    """Calculate BMI from height and linked weight entity."""

    def __init__(self, coordinator, height, weight_entity_id):
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self.height = height  # meters
        self.weight_entity_id = weight_entity_id
        self._attr_name = "WalkingPad BMI"
        self._attr_unique_id = f"{coordinator.mac}_bmi"
        self._attr_native_unit_of_measurement = "kg/m²"
        self._attr_icon = "mdi:human-male-height"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        """Register for updates from both treadmill and weight sensor."""
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        async_track_state_change_event(
            self.hass,
            [self.weight_entity_id],
            self._handle_weight_update
        )
        self._recalculate_bmi()
        self.async_write_ha_state()

    @callback
    def _handle_weight_update(self, entity_id, old_state, new_state):
        self._recalculate_bmi()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        self._recalculate_bmi()
        self.async_write_ha_state()

    def _recalculate_bmi(self):
        if not self.weight_entity_id:
            self._state = None
            return

        weight_state = self.hass.states.get(self.weight_entity_id)
        if not weight_state or weight_state.state in (None, "unknown", "unavailable"):
            self._state = None
            return

        try:
            weight_str = str(weight_state.state).replace("kg", "").strip()
            weight = float(weight_str)
            self._state = round(weight / (self.height ** 2), 2)
        except (ValueError, ZeroDivisionError):
            self._state = None


class WalkingPadBmiRatingSensor(SensorEntity):
    """BMI rating sensor based on calculated BMI value."""

    def __init__(self, coordinator, bmi_sensor: "WalkingPadBmiSensor"):
        self.coordinator = coordinator
        self.bmi_sensor = bmi_sensor
        self._attr_name = "WalkingPad BMI Rating"
        self._attr_unique_id = f"{coordinator.mac}_bmi_rating"
        self._attr_icon = "mdi:tag-text-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )
        self._state = None

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_update)
        self.hass.bus.async_listen("state_changed", self._handle_update_event)
        self._update_rating()
        self.async_write_ha_state()

    @callback
    def _handle_update(self):
        self._update_rating()
        self.async_write_ha_state()

    @callback
    def _handle_update_event(self, event):
        if event.data.get("entity_id") == self.bmi_sensor.entity_id:
            self._update_rating()
            self.async_write_ha_state()

    def _update_rating(self):
        bmi = self.bmi_sensor.native_value
        if bmi is None:
            self._state = None
            return

        if bmi < 18.5:
            self._state = "Underweight"
        elif 18.5 <= bmi < 25:
            self._state = "Normal weight"
        elif 25 <= bmi < 30:
            self._state = "Overweight"
        elif 30 <= bmi < 35:
            self._state = "Obese (Class I)"
        elif 35 <= bmi < 40:
            self._state = "Obese (Class II)"
        else:
            self._state = "Obese (Class III)"


class WalkingPadSensor(SensorEntity):
    ICON_MAP = {
        "speed": "mdi:run",
        "distance": "mdi:map-marker-distance",
        "energy": "mdi:fire",
    }

    def __init__(self, coordinator, key, name, unit, icon):
        self.coordinator = coordinator
        self._attr_name = f"WalkingPad {name}"
        self._attr_unique_id = f"{coordinator.mac}_{key}"
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = self.ICON_MAP.get(key, "mdi:gauge")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    async def async_update(self):
        pass

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)


class WalkingPadStepsSensor(SensorEntity):
    """Sensor to calculate steps from distance."""

    def __init__(self, coordinator, key, name, unit):
        self.coordinator = coordinator
        self._attr_name = f"WalkingPad {name}"
        self._attr_unique_id = f"{coordinator.mac}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:walk"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )

    @property
    def native_value(self):
        distance_m = self.coordinator.data.get("distance", 0)
        if distance_m is None:
            return None
        return math.floor(distance_m / STEP_LENGTH_METERS)

    async def async_update(self):
        pass

    @callback
    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self._handle_coordinator_update)


class WalkingPadEnergyTracker:
    """Tracks and accumulates energy, supports daily/weekly/monthly resets and persistence."""

    def __init__(self, hass, device_mac, update_callback):
        self.hass = hass
        self.device_mac = device_mac
        self._update_callback = update_callback

        # Initialize stored values and last known energy reading
        self.daily = 0.0
        self.weekly = 0.0
        self.monthly = 0.0
        self.total = 0.0
        self._last_energy = None

        # Setup resets at midnight / weekly / monthly
        async_track_time_change(hass, self._reset_daily, hour=0, minute=0, second=0)
        async_track_time_change(hass, self._reset_weekly_if_monday, hour=0, minute=0, second=0)
        async_track_time_change(hass, self._reset_monthly_if_first_day, hour=0, minute=0, second=0)

        

    @callback
    def _reset_daily(self, now):
        self.daily = 0.0
        self._update_callback()

    @callback
    def _reset_weekly_if_monday(self, now):
        # 'now' is a datetime.datetime object
        if now.weekday() == 0:  # Monday
            self._reset_weekly(now)

    @callback
    def _reset_weekly(self, now):
        self.weekly = 0.0
        self._update_callback()

    @callback
    def _reset_monthly_if_first_day(self, now):
        if now.day == 1:
            self._reset_monthly(now)


    @callback
    def _reset_monthly(self, now):
        self.monthly = 0.0
        self._update_callback()


    def add_energy(self, current_energy):
        """Add the difference (delta) between current and last reading to counters."""
        if current_energy is None:
            return

        try:
            current_energy = float(current_energy)
        except Exception:
            return

        if self._last_energy is None:
            # First reading, just set last_energy without adding
            self._last_energy = current_energy
            return

        delta = current_energy - self._last_energy
        # Sometimes device resets energy count, delta may be negative
        if delta < 0:
            delta = current_energy  # assume restart, count full current

        self.daily += delta
        self.weekly += delta
        self.monthly += delta
        self.total += delta

        self._last_energy = current_energy


class WalkingPadEnergyAggregateSensor(RestoreEntity, SensorEntity):
    """Aggregated energy sensor for daily, weekly, monthly, total."""

    ICON_MAP = {
        "daily": "mdi:calendar-today",
        "weekly": "mdi:calendar-week",
        "monthly": "mdi:calendar-month",
        "total": "mdi:counter",
    }

    def __init__(self, coordinator, tracker, key, name):
        self.coordinator = coordinator
        self.tracker = tracker
        self.key = key  # 'daily', 'weekly', 'monthly', or 'total'
        self._attr_name = f"WalkingPad {name}"
        self._attr_unique_id = f"{coordinator.mac}_energy_{key}"
        self._attr_native_unit_of_measurement = "kcal"
        self._attr_icon = self.ICON_MAP.get(key, "mdi:fire")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            name=coordinator.device_name,
            manufacturer="KingSmith",
            model="WalkingPad MC11"
        )
        self._state = None

    @property
    def native_value(self):
        return int(getattr(self.tracker, self.key))

    async def async_added_to_hass(self):
        # Restore previous state to keep totals on restart
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in ("unknown", "unavailable"):
            try:
                setattr(self.tracker, self.key, float(last_state.state))
            except ValueError:
                pass

        self.coordinator.async_add_listener(self._handle_update)

    @callback
    def _handle_update(self):
        energy = self.coordinator.data.get("energy")
        self.tracker.add_energy(energy)
        self.async_write_ha_state()
