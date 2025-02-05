import asyncio

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.fan import FanEntity
from homeassistant.const import *
from homeassistant.core import Config
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.util.unit_system import IMPERIAL_SYSTEM

from custom_components.sonoff.binary_sensor import XRemoteSensor, XBinarySensor
from custom_components.sonoff.climate import XClimateNS
from custom_components.sonoff.core import devices
from custom_components.sonoff.core.ewelink.base import *
from custom_components.sonoff.cover import XCover
from custom_components.sonoff.fan import XFan
from custom_components.sonoff.light import *
from custom_components.sonoff.sensor import XSensor, XRemoteButton, XUnknown
from custom_components.sonoff.switch import *

DEVICEID = "1000123abc"


class DummyHass:
    def __init__(self):
        # noinspection PyTypeChecker
        self.config = Config(None)
        self.data = {}

        self.states = self
        self.async_set = lambda *args: None

        self.bus = self
        self.async_fire = lambda *args: None


class DummyRegistry(XRegistry):
    def __init__(self):
        # noinspection PyTypeChecker
        super().__init__(None)
        self.send_args = None

    async def send(self, *args):
        self.send_args = args

    def call(self, coro):
        asyncio.get_event_loop().run_until_complete(coro)
        return self.send_args


# noinspection PyTypeChecker
def get_entitites(device: dict, config: dict = None) -> list:
    device.setdefault("name", "Device1")
    device.setdefault("deviceid", DEVICEID)
    device.setdefault("online", True)
    device.setdefault("extra", {"uiid": 0})
    params = device.setdefault("params", {})
    params.setdefault("staMac", "FF:FF:FF:FF:FF:FF")

    entities = []

    asyncio.create_task = lambda _: None

    reg = DummyRegistry()
    reg.config = config
    reg.dispatcher_connect(SIGNAL_ADD_ENTITIES, lambda x: entities.extend(x))
    reg.setup_devices([device])

    hass = DummyHass()
    for entity in entities:
        entity.hass = hass

    return entities


def await_(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_simple_switch():
    entities = get_entitites({
        'name': 'Kitchen',
        'extra': {'uiid': 1, 'model': 'PSF-BD1-GL'},
        'brandName': 'SONOFF',
        'productModel': 'MINI',
        'online': True,
        'params': {
            'sledOnline': 'on',
            'switch': 'on',
            'fwVersion': '3.3.0',
            'rssi': -39,
            'startup': 'off',
            'init': 1,
            'pulse': 'off',
            'pulseWidth': 3000,
            'staMac': '11:22:33:AA:BB:CC'
        },
    })
    assert len(entities) == 3

    switch: XSwitch = entities[0]
    assert switch.name == "Kitchen"
    assert switch.unique_id == DEVICEID
    assert (CONNECTION_NETWORK_MAC, "11:22:33:AA:BB:CC") in \
           switch.device_info["connections"]
    assert switch.device_info["manufacturer"] == "SONOFF"
    assert switch.device_info["model"] == "MINI"
    assert switch.device_info["sw_version"] == "3.3.0"
    assert switch.state == "on"

    led: XToggle = next(e for e in entities if e.uid == "led")
    assert led.unique_id == DEVICEID + "_led"
    assert led.state == "on"
    assert led.entity_registry_enabled_default is False

    rssi: XSensor = next(e for e in entities if e.uid == "rssi")
    assert rssi.unique_id == DEVICEID + "_rssi"
    assert rssi.native_value == -39
    assert rssi.entity_registry_enabled_default is False


def test_available():
    entities = get_entitites({
        'extra': {'uiid': 1},
        'params': {'switch': 'on'},
    })
    switch: XSwitch = entities[0]
    assert switch.available is False
    assert switch.state == "on"

    switch.ewelink.cloud.online = True
    switch.ewelink.cloud.dispatcher_send(SIGNAL_CONNECTED)

    # only cloud online changed
    msg = {"deviceid": DEVICEID, "params": {"online": False}}
    switch.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, msg)
    assert switch.available is False
    assert switch.state == "on"

    # cloud state changed (also change available)
    msg = {"deviceid": DEVICEID, "params": {"switch": "off"}}
    switch.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, msg)
    assert switch.available is True
    assert switch.state == "off"


def test_nospec():
    device = {"extra": {"uiid": 0}, "params": {"switch": "on"}}
    entities = get_entitites(device)

    switch: XSwitch = entities[0]
    assert switch.state == "on"

    device = {"extra": {"uiid": 0}, "params": {"property": 123}}
    entities = get_entitites(device)

    sensor: XUnknown = entities[0]
    assert len(sensor.state) == 25
    assert sensor.extra_state_attributes["property"] == 123


def test_switch_2ch():
    entities = get_entitites({
        'extra': {'uiid': 2},
        'params': {
            'switches': [
                {'switch': 'on', 'outlet': 0},
                {'switch': 'off', 'outlet': 1},
                {'switch': 'off', 'outlet': 2},
                {'switch': 'off', 'outlet': 3}
            ],
        },
        'tags': {
            'ck_channel_name': {'0': 'Channel A', '1': 'Channel B'}
        }
    })

    switch1: XSwitch = entities[0]
    assert switch1.name == "Channel A"
    assert switch1.unique_id == DEVICEID + "_1"
    assert switch1.state == "on"

    switch2: XSwitch = entities[1]
    assert switch2.name == "Channel B"
    assert switch2.unique_id == DEVICEID + "_2"
    assert switch2.state == "off"

    switch2.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"switches": [{"outlet": 1, "switch": "on"}]}
    })
    assert switch2.state == "on"


def test_fan():
    entities = get_entitites({
        'extra': {'uiid': 34, 'model': 'PSF-BFB-GL'},
        'params': {
            'sledOnline': 'on',
            'fwVersion': '3.5.0',
            'rssi': -47,
            'switches': [
                {'switch': 'off', 'outlet': 0},
                {'switch': 'off', 'outlet': 1},
                {'switch': 'off', 'outlet': 2},
                {'switch': 'on', 'outlet': 3}
            ],
            'configure': [
                {'startup': 'on', 'outlet': 0},
                {'startup': 'off', 'outlet': 1},
                {'startup': 'stay', 'outlet': 2},
                {'startup': 'stay', 'outlet': 3}
            ],
        },
    })

    fan: XFan = entities[0]
    assert fan.state == "off"
    assert fan.state_attributes["percentage"] == 0
    assert fan.state_attributes["preset_mode"] is None

    fan.set_state({'switches': [
        {'switch': 'off', 'outlet': 0},
        {'switch': 'on', 'outlet': 1},
        {'switch': 'on', 'outlet': 2},
        {'switch': 'off', 'outlet': 3}
    ]})
    assert fan.state == "on"
    assert fan.state_attributes["percentage"] == 66
    assert fan.state_attributes["preset_mode"] == "medium"

    fan.set_state({"fan": "on", "speed": 3})
    assert fan.state_attributes["percentage"] == 100
    assert fan.state_attributes["preset_mode"] == "high"

    light: XSwitches = next(e for e in entities if e.uid == "1")
    assert light.state == "off"
    assert isinstance(light, LightEntity)

    fan.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"light": "on"}
    })
    assert light.state == "on"

    fan.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"fan": "off"}
    })
    assert fan.state == "off"

    fan.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {'switches': [
            {'switch': 'off', 'outlet': 0},
            {'switch': 'on', 'outlet': 1},
            {'switch': 'off', 'outlet': 2},
            {'switch': 'off', 'outlet': 3}
        ]}
    })
    assert fan.state == "on"
    assert fan.state_attributes["percentage"] == 33
    assert fan.state_attributes["preset_mode"] == "low"
    assert light.state == "off"


def test_sonoff_th():
    entities = get_entitites({
        'name': 'Sonoff TH',
        'deviceid': DEVICEID,
        'extra': {'uiid': 15, 'model': 'PSA-BHA-GL'},
        'brandName': 'SONOFF',
        'productModel': 'TH16',
        'online': True,
        'params': {
            'currentHumidity': '42',
            'currentTemperature': '14.6',
            'deviceType': 'normal',
            'fwVersion': '3.4.0',
            'init': 1,
            'mainSwitch': 'off',
            'pulse': 'off',
            'pulseWidth': 500,
            'rssi': -43,
            'sensorType': 'AM2301',
            'sledOnline': 'on',
            'startup': 'stay',
            'switch': 'off',
            'targets': [
                {'reaction': {'switch': 'off'}, 'targetHigh': '22'},
                {'reaction': {'switch': 'on'}, 'targetLow': '22'}
            ],
            "timers": [],
            "version": 8
        },
    })

    switch: XSwitchTH = entities[0]
    assert switch.state == "off"

    temp: XSensor = next(e for e in entities if e.uid == "temperature")
    assert temp.state == 14.6

    # test round to 1 digit
    temp.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"deviceType": "normal", "temperature": 12.34}
    })
    assert temp.state == 12.3

    temp.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"deviceType": "normal", "temperature": -273}
    })
    assert temp.state == 12.3

    hum: XSensor = next(e for e in entities if e.uid == "humidity")
    assert hum.state == 42

    # check TH v3.4.0 param name
    temp.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"deviceType": "normal", "humidity": 48}
    })
    assert hum.state == 48

    # check TH v3.4.0 zero humidity bug (skip value)
    temp.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"deviceType": "normal", "humidity": 0}
    })
    assert hum.state == 48

    temp.ewelink.local.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"deviceType": "normal", "currentHumidity": "unavailable"}
    })
    assert hum.state is None


def test_dual_r3():
    # noinspection DuplicatedCode
    entities = get_entitites({
        'extra': {'uiid': 126},
        'params': {
            'version': 7,
            'workMode': 1,
            'motorSwMode': 2,
            'motorSwReverse': 0,
            'outputReverse': 0,
            'motorTurn': 0,
            'calibState': 0,
            'currLocation': 0,
            'location': 0,
            'sledBright': 100,
            'rssi': -35,
            'overload_00': {
                'minActPow': {'enabled': 0, 'value': 10},
                'maxVoltage': {'enabled': 0, 'value': 24000},
                'minVoltage': {'enabled': 0, 'value': 10},
                'maxCurrent': {'enabled': 0, 'value': 1500},
                'maxActPow': {'enabled': 0, 'value': 360000}
            },
            'overload_01': {
                'minActPow': {'enabled': 0, 'value': 10},
                'maxVoltage': {'enabled': 0, 'value': 24000},
                'minVoltage': {'enabled': 0, 'value': 10},
                'maxCurrent': {'enabled': 0, 'value': 1500},
                'maxActPow': {'enabled': 0, 'value': 360000}
            },
            'oneKwhState_00': 0, 'startTime_00': '', 'endTime_00': '',
            'oneKwhState_01': 0, 'startTime_01': '', 'endTime_01': '',
            'oneKwhData_00': 0, 'oneKwhData_01': 0, 'current_00': 0,
            'voltage_00': 24762, 'actPow_00': 0, 'reactPow_00': 0,
            'apparentPow_00': 0, 'current_01': 0, 'voltage_01': 24762,
            'actPow_01': 0, 'reactPow_01': 0, 'apparentPow_01': 0,
            'fwVersion': '1.3.0', 'timeZone': 3, 'swMode_00': 2,
            'swMode_01': 2, 'swReverse_00': 0, 'swReverse_01': 0,
            'zyx_clear_timers': True,
            'switches': [
                {'switch': 'off', 'outlet': 0},
                {'switch': 'off', 'outlet': 1}
            ],
            'configure': [
                {'startup': 'off', 'outlet': 0},
                {'startup': 'off', 'outlet': 1}
            ],
            'pulses': [
                {'pulse': 'off', 'width': 1000, 'outlet': 0},
                {'pulse': 'off', 'width': 1000, 'outlet': 1}
            ],
            'getKwh_00': 2,
            'uiActive': {'time': 120, 'outlet': 0},
            'initSetting': 1,
            'getKwh_01': 2,
            'calibration': 1
        },
    })

    volt: XSensor = next(e for e in entities if e.uid == "voltage_1")
    assert volt.state == 247.62


def test_diffuser():
    entitites = get_entitites({
        'extra': {'uiid': 25},
        'params': {
            'lightbright': 254,
            'lightBcolor': 255,
            'lightGcolor': 217,
            'lightRcolor': 7,
            'lightmode': 2,
            'lightswitch': 0,
            'water': 0,
            'state': 2,
            'switch': 'off',
            'staMac': '11:22:33:AA:BB:CC',
            'fwVersion': '3.4.0',
            'rssi': -88,
            'sledOnline': 'on',
            'version': 8,
            'only_device': {'ota': 'success'},
        }
    })

    light = next(e for e in entitites if isinstance(e, XDiffuserLight))
    assert light.state == "off"


def test_sonoff_sc():
    entities = get_entitites({
        "extra": {"uiid": 18},
        "params": {
            "dusty": 2,
            "fwVersion": "2.7.0",
            "humidity": 92,
            "light": 10,
            "noise": 2,
            "rssi": -34,
            "sledOnline": "on",
            "staMac": "11:22:33:AA:BB:CC",
            "temperature": 25
        },
    })
    temp: XSensor = next(e for e in entities if e.uid == "temperature")
    assert temp.state == 25
    hum: XSensor = next(e for e in entities if e.uid == "humidity")
    assert hum.state == 92
    dusty: XSensor = next(e for e in entities if e.uid == "dusty")
    assert dusty.state == 2
    light: XSensor = next(e for e in entities if e.uid == "light")
    assert light.state == 10
    noise: XSensor = next(e for e in entities if e.uid == "noise")
    assert noise.state == 2


def test_sonoff_pow():
    entities = get_entitites({
        "extra": {"uiid": 32},
        "params": {
            "hundredDaysKwh": "get",
            "startTime": "2020-05-28T13:19:55.409Z",
            "endTime": "2020-05-28T18:24:24.429Z",
            "timeZone": 2,
            "uiActive": 60,
            "oneKwh": "stop",
            "current": "1.23",
            "voltage": "234.20",
            "power": "12.34",
            "pulseWidth": 500,
            "pulse": "off",
            "startup": "on",
            "switch": "on",
            "alarmPValue": [-1, -1],
            "alarmCValue": [-1, -1],
            "alarmVValue": [-1, -1],
            "alarmType": "pcv",
            "init": 1,
            "rssi": -72,
            "fwVersion": "3.4.0",
            "sledOnline": "on",
            "version": 8
        },
    })

    power: XSensor = next(e for e in entities if e.uid == "power")
    assert power.state == 12.34
    power: XSensor = next(e for e in entities if e.uid == "current")
    assert power.state == 1.23


def test_rfbridge():
    entities = get_entitites({
        "extra": {"uiid": 28},
        "params": {
            "cmd": "trigger",
            "fwVersion": "3.4.0",
            "init": 1,
            "rfChl": 0,
            "rfList": [],
            "rfTrig0": "2020-05-10T19:29:43.000Z",
            "rfTrig1": 0,
            "rssi": -55,
            "setState": "arm",
            "sledOnline": "on",
            "timers": [],
            "version": 8
        },
        "tags": {
            "disable_timers": [],
            "zyx_info": [{
                "buttonName": [{"0": "Button1"}],
                "name": "Alarm1",
                "remote_type": "6"
            }, {
                "buttonName": [{"1": "Button1"}],
                "name": "Alarm2",
                "remote_type": "6"
            }]
        }
    }, {
        "rfbridge": {
            "Alarm1": {
                "name": "Custom1",
                "timeout": 0,
                "payload_off": "Alarm2"
            }
        }
    })

    alarm: XRemoteSensor = next(e for e in entities if e.name == "Custom1")
    assert alarm.state == "off"

    alarm.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"cmd": "trigger", "rfTrig0": "2022-04-19T03:56:52.000Z"}
    })
    assert alarm.state == "on"

    alarm.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {"cmd": "trigger", "rfTrig1": "2022-04-19T03:57:52.000Z"}
    })
    assert alarm.state == "off"


def test_wifi_sensor():
    entities = get_entitites({
        "extra": {"uiid": 102},
        "params": {
            "actionTime": "2020-05-20T08:43:33.151Z",
            "battery": 3,
            "fwVersion": "1000.2.917",
            "lastUpdateTime": "2020-05-20T13:43:24.124Z",
            "rssi": -64,
            "switch": "off",
            "type": 4
        }
    }, {
        "devices": {
            DEVICEID: {"device_class": "window"}
        }
    })

    sensor: XBinarySensor = entities[0]
    assert sensor.state == "off"
    assert sensor.device_class == BinarySensorDeviceClass.WINDOW


def test_zigbee_button():
    entities = get_entitites({
        "extra": {"uiid": 1000},
        "params": {
            "battery": 100,
            "trigTime": "1601263115917",
            "key": 0
        }
    })

    button: XRemoteButton = entities[0]
    assert button.state == ""

    button.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {'trigTime': '1601285000235', 'key': 1}
    })
    assert button.state == "double"


def test_sonoff_r5():
    entities = get_entitites({
        "extra": {"uiid": 174},
        "params": {
            'subDevId': '7007ad88', 'parentid': '10015c1cfc',
            'bleAddr': '7007AD88', 'outlet': 3, 'key': 0, 'count': 181,
            'actionTime': '2022-04-11T13:51:08.986Z'
        }
    })

    button: XRemoteButton = entities[0]
    assert button.state == ""

    button.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {
            'bleAddr': '7007AD88', 'outlet': 2, 'key': 1, 'count': 883,
            'actionTime': '2022-04-12T11:17:45.831Z'
        }
    })
    assert button.state == "button_3_double"


def test_zigbee_th():
    entities = get_entitites({
        "extra": {"uiid": 1770},
        "params": {
            "humidity": "6443",
            "temperature": "2096",
            "trigTime": "1594745697262",
            "battery": 127,
        }
    })

    temp: XSensor = entities[0]
    assert temp.state == 20.96

    hum: XSensor = entities[1]
    assert hum.state == 64.43

    bat: XSensor = entities[2]
    assert bat.state == 127


def test_zigbee_motion():
    entities = get_entitites({
        "extra": {"uiid": 2026},
        "params": {
            "battery": 100,
            "trigTime": "1595266029933",
            "motion": 0,
        }
    }, {
        "devices": {
            DEVICEID: {"device_class": "occupancy"}
        }
    })

    motion: XBinarySensor = entities[0]
    assert motion.state == "off"
    assert motion.device_class == BinarySensorDeviceClass.OCCUPANCY

    motion.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID,
        "params": {'trigTime': '1601285000235', 'motion': 1}
    })
    assert motion.state == "on"

    motion.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {'online': False}
    })
    assert motion.state == "off"


def test_default_class():
    devices.set_default_class("light")

    entities = get_entitites({"extra": {"uiid": 15}})
    assert isinstance(entities[0], XSwitchTH)
    assert isinstance(entities[0], LightEntity)
    assert not isinstance(entities[0], SwitchEntity)

    entities = get_entitites({
        "extra": {"uiid": 1}
    }, {
        "devices": {
            DEVICEID: {"device_class": "switch"}
        }
    })
    assert isinstance(entities[0], SwitchEntity)
    assert not isinstance(entities[0], LightEntity)

    # restore changes
    devices.set_default_class("switch")


def test_device_class():
    entities = get_entitites({
        "extra": {"uiid": 15}
    }, {
        "devices": {
            DEVICEID: {"device_class": "light"}
        }
    })

    light: XSwitchTH = entities[0]
    # Hass v2021.12 - off, Hass v2022.2 and more - None
    assert light.state in (None, "off")

    light.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"switch": "on"}
    })
    assert light.state == "on"

    assert light.__class__.__init__ == XEntity.__init__
    assert light.__class__.set_state == XSwitch.set_state
    assert light.__class__.async_turn_on == XSwitchTH.async_turn_on

    assert isinstance(light, LightEntity)
    assert not isinstance(light, SwitchEntity)


def test_device_class_micro():
    # Sonoff Micro has multichannel firmware
    for device_class in ("light", ["light"]):
        entities = get_entitites({
            "extra": {"uiid": 77},
            "params": {
                "switches": [{'switch': 'on', 'outlet': 0}]
            }
        }, {
            "devices": {
                DEVICEID: {"device_class": device_class}
            }
        })

        light: XSwitches = next(e for e in entities if e.uid == "1")
        assert light.state == "on"

        light.set_state({"switches": [{'switch': 'off', 'outlet': 0}]})
        assert light.state == "off"

        assert isinstance(light, LightEntity)


def test_device_class2():
    classes = {
        2: XSwitches.async_turn_on,
        4256: XZigbeeSwitches.async_turn_on
    }
    for uiid, func in classes.items():
        entities = get_entitites({
            "extra": {"uiid": uiid},
            "params": {
                'switches': [
                    {'switch': 'on', 'outlet': 0},
                    {'switch': 'on', 'outlet': 1},
                    {'switch': 'off', 'outlet': 2},
                    {'switch': 'off', 'outlet': 3}
                ],
            }
        }, {
            "devices": {
                DEVICEID: {"device_class": ["light", "fan"]}
            }
        })

        light: XSwitches = next(e for e in entities if e.uid == "1")
        assert isinstance(light, LightEntity)
        assert light.state == "on"

        fan: XSwitches = next(e for e in entities if e.uid == "2")
        assert isinstance(fan, FanEntity)
        assert fan.state == "on"

        assert light.__class__.async_turn_on == func


def test_light_group():
    entities = get_entitites({
        "extra": {"uiid": 2},
        "params": {
            'switches': [
                {'switch': 'on', 'outlet': 0},
                {'switch': 'on', 'outlet': 1},
                {'switch': 'off', 'outlet': 2},
                {'switch': 'off', 'outlet': 3}
            ],
        }
    }, {
        "devices": {
            DEVICEID: {"device_class": [{"light": [2, 1]}]}
        }
    })

    light: XLightGroup = next(e for e in entities if e.uid == "21")
    assert light.state == "on" and light.brightness == 255

    # noinspection PyTypeChecker
    registry: DummyRegistry = light.ewelink

    await_(light.async_turn_on(brightness=128))
    assert registry.send_args[1]["switches"] == [
        {'outlet': 1, 'switch': 'on'}, {'outlet': 0, 'switch': 'off'}
    ]
    assert light.brightness == 128

    await_(light.async_turn_on(brightness=0))
    assert registry.send_args[1]["switches"] == [
        {'outlet': 1, 'switch': 'off'}, {'outlet': 0, 'switch': 'off'}
    ]

    await_(light.async_turn_on())
    assert registry.send_args[1]["switches"] == [
        {'outlet': 1, 'switch': 'on'}, {'outlet': 0, 'switch': 'on'}
    ]


def test_diy_device():
    reg = DummyRegistry()
    reg.config = {
        "devices": {
            DEVICEID: {
                "name": "MyDIY",
                "device_class": "light"
            }
        }
    }

    entities = []
    reg.dispatcher_connect(SIGNAL_ADD_ENTITIES, lambda x: entities.extend(x))

    reg.local.dispatcher_send(SIGNAL_UPDATE, {
        "host": "192.168.1.123",
        "deviceid": DEVICEID,
        "diy": "diy_plug",
        "params": {"switch": "on"}
    })

    switch: XSwitch = entities[0]
    assert switch.name == "MyDIY"
    assert switch.state == "on"
    assert isinstance(switch, LightEntity)


def test_unknown_diy():
    reg = DummyRegistry()

    entities = []
    reg.dispatcher_connect(SIGNAL_ADD_ENTITIES, lambda x: entities.extend(x))

    reg.local.dispatcher_send(SIGNAL_UPDATE, {
        "host": "192.168.1.123",
        "deviceid": DEVICEID,
        "diy": "dummy",
        "params": {"switch": "on"}
    })

    switch: XSwitch = entities[0]
    assert switch.name == "Unknown DIY"
    assert switch.device_info["model"] == "dummy"
    assert switch.state == "on"


def test_local_devicekey():
    reg = DummyRegistry()
    reg.config = {
        "devices": {
            DEVICEID: {
                "devicekey": "64271b79-89f6-4d18-8318-7d751faacd13",
                "device_class": "fan"
            }
        }
    }

    entities = []
    reg.dispatcher_connect(SIGNAL_ADD_ENTITIES, lambda x: entities.extend(x))

    reg.local.dispatcher_send(SIGNAL_UPDATE, {
        "host": "192.168.1.123",
        "deviceid": DEVICEID,
        "diy": "diy_plug",
        "iv": "3PgYPjEuE4qCoZOTsPE2xg==",
        "data": "t9YKDAK3nnURqivGN0evtaS+Yj4M6b6NUV+ptJlMTOQ=",
    })

    switch: XSwitch = entities[0]
    # await_(reg.local.send(switch.device, {"switch": "on"}))
    assert switch.name == "MINI DIY"
    assert switch.state == "on"
    assert isinstance(switch, FanEntity)


# https://www.avrfreaks.net/sites/default/files/forum_attachments/AT08550_ZigBee_Attribute_Reporting_0.pdf
def test_reporting():
    time.time = lambda: 0

    entities = get_entitites({
        'extra': {'uiid': 15},
        'params': {
            'currentTemperature': '14.6',
        },
    }, {
        "devices": {
            DEVICEID: {
                "reporting": {
                    "temperature": [5, 60, 0.5]
                }
            }
        }
    })

    temp: XSensor = next(e for e in entities if e.uid == "temperature")
    assert temp.state == 14.6

    # update in min report interval - no update
    temp.set_state({"temperature": 20})
    assert temp.state == 14.6

    # automatic update value after 30 seconds (Hass force_update logic)
    time.time = lambda: 30
    await_(temp.async_update())
    assert temp.state == 20

    # lower than reportable change value - no update
    time.time = lambda: 40
    temp.set_state({"temperature": 20.3})
    assert temp.state == 20

    # more than reportable change value - update
    temp.set_state({"temperature": 21})
    assert temp.state == 21

    # update after max report interval - update
    time.time = lambda: 140
    temp.set_state({"temperature": 21.1})
    assert temp.state == 21.1


def test_temperature_convert():
    entities = get_entitites({
        'extra': {'uiid': 15},
        'params': {
            'currentTemperature': '14.6',
        },
    })

    temp: XSensor = next(e for e in entities if e.uid == "temperature")
    assert temp.state == 14.6

    temp.hass.config.units = IMPERIAL_SYSTEM
    assert temp.state == 58.3
    assert temp.unit_of_measurement == TEMP_FAHRENHEIT


def test_ns_panel():
    entities = get_entitites({
        'extra': {'uiid': 133},
        'params': {
            'version': 8,
            'pulses': [
                {'pulse': 'off', 'width': 1000, 'outlet': 0},
                {'pulse': 'off', 'width': 1000, 'outlet': 1}
            ],
            'switches': [
                {'switch': 'on', 'outlet': 0},
                {'switch': 'on', 'outlet': 1}
            ],
            'configure': [
                {'startup': 'stay', 'outlet': 0},
                {'startup': 'stay', 'outlet': 1}
            ], 'lock': 0,
            'fwVersion': '1.2.0',
            'temperature': 20,
            'humidity': 50,
            'tempUnit': 0,
            'HMI_outdoorTemp': {'current': 7, 'range': '6,17'},
            'HMI_weather': 33,
            'cityId': '123456',
            'dst': 1,
            'dstChange': '2022-10-30T01:00:00.000Z',
            'geo': '12.3456,-12.3456',
            'timeZone': 0,
            'HMI_ATCDevice': {
                'ctype': 'device', 'id': '100xxxxxx', 'outlet': 0,
                'etype': 'cold'
            },
            'ctype': 'device',
            'id': '100xxxxxx',
            'resourcetype': 'ATC',
            'ATCEnable': 0,
            'ATCMode': 0,
            'ATCExpect0': 26,
            'HMI_dimEnable': 1,
            'HMI_resources': [
                {'ctype': 'device', 'id': '1000yyyyyy', 'uiid': 6},
                {'ctype': 'idle'},
                {'ctype': 'device', 'id': '1000zzzzzz', 'uiid': 1},
                {'ctype': 'scene', 'id': '61dd5af0b615852f758669d6'},
                {'ctype': 'idle'},
                {'ctype': 'idle'},
                {'ctype': 'idle'},
                {'ctype': 'scene', 'id': '61dd5b0ab615852f758669d8'}
            ],
            'ATCExpect1': -999, 'HMI_dimOpen': 0,
            'only_device': {'ota': 'success', 'ota_fail_reason': 0},
            'tempCorrection': -2,
            'cityStr': 'Sheffield'
        }
    })

    for uid in ("1", "2", "temperature"):
        assert any(e.uid == uid for e in entities)

    temp: XSensor = next(e for e in entities if e.uid == "outdoor_temp")
    assert temp.state == 7
    assert temp.extra_state_attributes == {"temp_min": 6, "temp_max": 17}

    clim: XClimateNS = next(e for e in entities if isinstance(e, XClimateNS))
    assert clim.state == "off"
    assert clim.state_attributes["current_temperature"] == 18
    assert clim.state_attributes["temperature"] == 26

    clim.internal_update({"tempCorrection": 2})
    assert clim.state_attributes["current_temperature"] == 22

    clim.internal_update({"ATCEnable": 1})
    assert clim.state == "cool"

    clim.internal_update({'ATCMode': 0, 'ATCExpect0': 22.22})
    assert clim.state_attributes["temperature"] == 22.2

    clim.internal_update({'ATCMode': 1})
    assert clim.state == "auto"
    # no target temperature
    assert clim.state_attributes == {"current_temperature": 22}


def test_cover():
    entities = get_entitites({
        'extra': {'uiid': 11},
        'params': {'switch': 'off', 'sequence': '123', 'setclose': 100}
    })

    cover: XCover = entities[0]
    assert cover.state == "closed"
    assert cover.state_attributes["current_position"] == 0

    cover.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"setclose": 30}
    })
    assert cover.state == "opening"
    assert cover.state_attributes["current_position"] == 0

    cover.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"sequence": "123", "setclose": 30}
    })
    assert cover.state == "open"
    assert cover.state_attributes["current_position"] == 70

    cover.ewelink.cloud.dispatcher_send(SIGNAL_UPDATE, {
        "deviceid": DEVICEID, "params": {"switch": "off"}
    })
    assert cover.state == "closing"
    assert cover.state_attributes["current_position"] == 70


def test_light_22():
    entities = get_entitites({
        "extra": {"uiid": 22},
        "params": {
            "channel0": "159",
            "channel1": "159",
            "channel2": "0",
            "channel3": "0",
            "channel4": "0",
            "state": "on",
            "type": "middle",
            "zyx_mode": 1
        }
    })

    light: XLightB1 = entities[0]
    assert light.state == "on"
    assert light.state_attributes["brightness"] == 149
    assert light.state_attributes["color_mode"] == COLOR_MODE_COLOR_TEMP
    assert light.state_attributes["color_temp"] == 2
    assert "effect" not in light.state_attributes

    params = UIID22_MODES["Good Night"]
    light.internal_update(params)
    assert light.state_attributes["brightness"] == 149  # don't change
    assert light.state_attributes["color_mode"] == COLOR_MODE_RGB
    assert light.state_attributes["effect"] == "Good Night"
    assert "color_temp" not in light.state_attributes

    # noinspection PyTypeChecker
    reg: DummyRegistry = light.ewelink
    assert reg.call(light.async_turn_on())[1] == {"state": "on"}
    assert reg.call(light.async_turn_on(effect="Good Night"))[1] == params


def test_light_l1():
    entities = get_entitites({
        "extra": {"uiid": 59},
        "params": {
            "bright": 100,
            "colorB": 255,
            "colorG": 255,
            "colorR": 255,
            "fwVersion": "2.9.1",
            "light_type": 1,
            "mode": 2,
            "rssi": -45,
            "sensitive": 8,
            "sledOnline": "on",
            "speed": 100,
            "switch": "on",
            "version": 8
        },
    })

    light: XLightL1 = entities[0]
    assert light.state == "on"
    assert light.state_attributes["brightness"] == 255
    assert light.state_attributes["effect"] == "Colorful Gradient"

    light.set_state({"switch": "off"})
    assert light.state == "off"
    assert light.state_attributes is None
