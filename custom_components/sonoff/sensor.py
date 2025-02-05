import asyncio
import time

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, \
    SensorStateClass
from homeassistant.const import *
from homeassistant.util import dt

from .core.const import DOMAIN
from .core.entity import XEntity
from .core.ewelink import XRegistry, SIGNAL_ADD_ENTITIES

PARALLEL_UPDATES = 0  # fix entity_platform parallel_updates Semaphore


async def async_setup_entry(hass, config_entry, add_entities):
    ewelink: XRegistry = hass.data[DOMAIN][config_entry.entry_id]
    ewelink.dispatcher_connect(
        SIGNAL_ADD_ENTITIES,
        lambda x: add_entities([e for e in x if isinstance(e, SensorEntity)])
    )


DEVICE_CLASSES = {
    "battery": SensorDeviceClass.BATTERY,
    "current": SensorDeviceClass.CURRENT,
    "current_1": SensorDeviceClass.CURRENT,
    "current_2": SensorDeviceClass.CURRENT,
    "humidity": SensorDeviceClass.HUMIDITY,
    "outdoor_temp": SensorDeviceClass.TEMPERATURE,
    "power": SensorDeviceClass.POWER,
    "power_1": SensorDeviceClass.POWER,
    "power_2": SensorDeviceClass.POWER,
    "rssi": SensorDeviceClass.SIGNAL_STRENGTH,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "voltage": SensorDeviceClass.VOLTAGE,
    "voltage_1": SensorDeviceClass.VOLTAGE,
    "voltage_2": SensorDeviceClass.VOLTAGE,
}

UNITS = {
    "battery": PERCENTAGE,
    "current": ELECTRIC_CURRENT_AMPERE,
    "current_1": ELECTRIC_CURRENT_AMPERE,
    "current_2": ELECTRIC_CURRENT_AMPERE,
    "humidity": PERCENTAGE,
    "outdoor_temp": TEMP_CELSIUS,
    "power": POWER_WATT,
    "power_1": POWER_WATT,
    "power_2": POWER_WATT,
    "rssi": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    "temperature": TEMP_CELSIUS,
    "voltage": ELECTRIC_POTENTIAL_VOLT,
    "voltage_1": ELECTRIC_POTENTIAL_VOLT,
    "voltage_2": ELECTRIC_POTENTIAL_VOLT,
}


class XSensor(XEntity, SensorEntity):
    """Class can convert string sensor value to float, multiply it and round if
    needed. Also class can filter incoming values using zigbee-like reporting
    logic: min report interval, max report interval, reportable change value.
    """
    multiply: float = None
    round: int = None

    report_ts = None
    report_mint = None
    report_maxt = None
    report_delta = None
    report_value = None

    def __init__(self, ewelink: XRegistry, device: dict):
        XEntity.__init__(self, ewelink, device)

        self._attr_device_class = DEVICE_CLASSES.get(self.uid)

        if self.uid in UNITS:
            # by default all sensors with units is measurement sensors
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UNITS[self.uid]

        reporting = device.get("reporting", {}).get(self.uid)
        if reporting:
            self.report_mint, self.report_maxt, self.report_delta = reporting
            self.report_ts = time.time()
            self._attr_force_update = True

    def set_state(self, params: dict = None, value: float = None):
        if params:
            try:
                value = float(params[self.param])
                if self.multiply:
                    value *= self.multiply
                if self.round is not None:
                    # convert to int when round is zero
                    value = round(value, self.round or None)
            except (TypeError, ValueError):
                pass

        if self.report_ts is not None:
            ts = time.time()

            if (ts - self.report_ts < self.report_mint) or (
                    ts - self.report_ts < self.report_maxt and
                    value is not None and
                    self._attr_native_value is not None and
                    abs(value - self._attr_native_value) <= self.report_delta
            ):
                self.report_value = value
                return

            self.report_value = None
            self.report_ts = ts

        self._attr_native_value = value

    async def async_update(self):
        if self.report_value is not None:
            XSensor.set_state(self, value=self.report_value)


class XTemperatureTH(XSensor):
    params = {"currentTemperature", "temperature"}
    uid = "temperature"

    def set_state(self, params: dict = None, value: float = None):
        try:
            # can be int, float, str or undefined
            value = params.get("currentTemperature") or params["temperature"]
            value = float(value)
            # filter zero values
            # https://github.com/AlexxIT/SonoffLAN/issues/110
            # filter wrong values
            # https://github.com/AlexxIT/SonoffLAN/issues/683
            if value != 0 and -270 < value < 270:
                XSensor.set_state(self, value=round(value, 1))
        except Exception:
            XSensor.set_state(self)


class XHumidityTH(XSensor):
    params = {"currentHumidity", "humidity"}
    uid = "humidity"

    def set_state(self, params: dict = None, value: float = None):
        try:
            value = params.get("currentHumidity") or params["humidity"]
            value = int(value)
            # filter zero values
            # https://github.com/AlexxIT/SonoffLAN/issues/110
            if value != 0:
                XSensor.set_state(self, value=value)
        except Exception:
            XSensor.set_state(self)


class XEnergySensor(XEntity, SensorEntity):
    get_params = None
    next_ts = 0

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_should_poll = True

    def set_state(self, params: dict):
        value = params[self.param]
        try:
            self._attr_native_value = round(
                int(value[0:2], 16) + int(value[2:4], 16) * 0.01 +
                int(value[4:6], 16) * 0.0001, 2
            )
        except Exception:
            pass

    async def async_update(self):
        ts = time.time()
        if ts > self.next_ts and self.ewelink.cloud.online:
            self.next_ts = ts + 3600
            await self.ewelink.cloud.send(self.device, self.get_params)


class XNSOutdoorTemp(XSensor):
    param = "HMI_outdoorTemp"
    uid = "outdoor_temp"

    # noinspection PyMethodOverriding
    def set_state(self, params: dict):
        try:
            value = params[self.param]
            self._attr_native_value = value["current"]

            mint, maxt = value["range"].split(",")
            self._attr_extra_state_attributes = {
                "temp_min": int(mint),
                "temp_max": int(maxt)
            }
        except Exception:
            pass


BUTTON_STATES = ["single", "double", "hold"]


class XRemoteButton(XEntity, SensorEntity):
    def __init__(self, ewelink: XRegistry, device: dict):
        XEntity.__init__(self, ewelink, device)
        self.params = {"key"}
        self._attr_native_value = ""

    def set_state(self, params: dict):
        button = params.get("outlet")
        key = BUTTON_STATES[params["key"]]
        self._attr_native_value = f"button_{button + 1}_{key}" \
            if button is not None else key
        asyncio.create_task(self.clear_state())

    async def clear_state(self):
        await asyncio.sleep(.5)
        self._attr_native_value = ""
        self._async_write_ha_state()


class XUnknown(XEntity, SensorEntity):
    _attr_device_class = DEVICE_CLASS_TIMESTAMP

    def internal_update(self, params: dict = None):
        self._attr_native_value = dt.utcnow()

        if params is not None:
            params.pop("bindInfos", None)
            self._attr_extra_state_attributes = params

        if self.hass:
            self._async_write_ha_state()
