"""
Each device has a specification - list of classes (XEntity childs). Platform
will setup entity if it isinstance() of platform entity class.

User can override SwitchEntity of any device via YAML (device_class option).

XEntity properties:
- params - required, set of parameters that this entity can read
- param - optional, entity main parameter (useful for sensors)
- uid - optional, entity unique_id tail

Developer can change global properties of existing classes via spec function.
"""
from typing import Optional

from ..binary_sensor import *
from ..climate import XClimateTH, XClimateNS
from ..cover import XCover, XCoverDualR3
from ..fan import XFan, XDiffuserFan, XToggleFan
from ..light import *
from ..remote import XRemote
from ..sensor import *
from ..switch import *

# supported custom device_class
DEVICE_CLASS = {
    "binary_sensor": (XEntity, BinarySensorEntity),
    "fan": (XToggleFan,),  # using custom class for overriding is_on function
    "light": (XEntity, LightEntity),
    "sensor": (XEntity, SensorEntity),
    "switch": (XEntity, SwitchEntity),
}


def spec(cls, base: str = None, enabled: bool = None, **kwargs) -> type:
    """Make duplicate for cls class with changes in kwargs params.

    If `base` param provided - can change Entity base class for cls. So it can
    be added to different Hass domain.
    """
    if enabled is not None:
        kwargs["_attr_entity_registry_enabled_default"] = enabled
    if base:
        bases = cls.__mro__[-len(XSwitch.__mro__)::-1]
        bases = {k: v for b in bases for k, v in b.__dict__.items()}
        return type(cls.__name__, DEVICE_CLASS[base], {**bases, **kwargs})
    return type(cls.__name__, (cls,), {**cls.__dict__, **kwargs})


Switch1 = spec(XSwitches, channel=0, uid="1")
Switch2 = spec(XSwitches, channel=1, uid="2")
Switch3 = spec(XSwitches, channel=2, uid="3")
Switch4 = spec(XSwitches, channel=3, uid="4")

XSensor100 = spec(XSensor, multiply=0.01, round=2)

Battery = spec(XSensor, param="battery")
LED = spec(XToggle, param="sledOnline", uid="led", enabled=False)
RSSI = spec(XSensor, param="rssi", enabled=False)

SPEC_SWITCH = [XSwitch, LED, RSSI]
SPEC_1CH = [Switch1, LED, RSSI]
SPEC_2CH = [Switch1, Switch2, LED, RSSI]
SPEC_3CH = [Switch1, Switch2, Switch3, LED, RSSI]
SPEC_4CH = [Switch1, Switch2, Switch3, Switch4, LED, RSSI]

# https://github.com/CoolKit-Technologies/eWeLink-API/blob/main/en/UIIDProtocol.md
DEVICES = {
    1: SPEC_SWITCH,
    2: SPEC_2CH,
    3: SPEC_3CH,
    4: SPEC_4CH,
    5: SPEC_SWITCH,
    6: SPEC_SWITCH,
    7: SPEC_2CH,  # Sonoff T1 2CH
    8: SPEC_3CH,  # Sonoff T1 3CH
    9: SPEC_4CH,
    11: [XCover, LED, RSSI],  # King Art - King Q4 Cover (only cloud)
    14: SPEC_SWITCH,  # Sonoff Basic (3rd party)
    15: [
        XSwitchTH, XClimateTH, XTemperatureTH, XHumidityTH, LED, RSSI,
    ],  # Sonoff TH16
    18: [
        spec(XSensor, param="temperature"),
        spec(XSensor, param="humidity"),
        spec(XSensor, param="dusty"),
        spec(XSensor, param="light"),
        spec(XSensor, param="noise"),
    ],
    22: [XLightB1, RSSI],  # Sonoff B1 (only cloud)
    # https://github.com/AlexxIT/SonoffLAN/issues/173
    25: [XDiffuserFan, XDiffuserLight, XWater, RSSI],  # Diffuser
    28: [XRemote, LED, RSSI],  # Sonoff RF Brigde 433
    29: SPEC_2CH,
    30: SPEC_3CH,
    31: SPEC_4CH,
    32: [
        XSwitch, LED, RSSI,
        spec(XSensor, param="current"),
        spec(XSensor, param="power"),
        spec(XSensor, param="voltage"),
        spec(XEnergySensor, param="hundredDaysKwhData", uid="energy",
             get_params={"hundredDaysKwh": "get"}),
    ],  # Sonoff Pow
    34: [
        XFan, XFanLight, LED, RSSI,
    ],  # Sonoff iFan02 and iFan03
    36: [XDimmer, RSSI],  # KING-M4 (dimmer, only cloud)
    44: [XLightD1, RSSI],  # Sonoff D1
    57: [XLight57, RSSI],  # Mosquito Killer Lamp
    59: [XLightL1, RSSI],  # Sonoff LED (only cloud)
    # 66: switch1,  # ZigBee Bridge
    77: SPEC_1CH,  # Sonoff Micro
    78: SPEC_1CH,  # https://github.com/AlexxIT/SonoffLAN/issues/615
    81: SPEC_1CH,
    82: SPEC_2CH,
    83: SPEC_3CH,
    84: SPEC_4CH,
    102: [XWiFiDoor, Battery, RSSI],  # Sonoff DW2 Door/Window sensor
    103: [XLightB02, RSSI],  # Sonoff B02 CCT bulb
    104: [XLightB05B, RSSI],  # Sonoff B05-B RGB+CCT color bulb
    107: SPEC_1CH,
    126: [
        Switch1, Switch2, RSSI,
        spec(XSensor100, param="current_00", uid="current_1"),
        spec(XSensor100, param="current_01", uid="current_2"),
        spec(XSensor100, param="voltage_00", uid="voltage_1"),
        spec(XSensor100, param="voltage_01", uid="voltage_2"),
        spec(XSensor100, param="actPow_00", uid="power_1"),
        spec(XSensor100, param="actPow_01", uid="power_2"),
        spec(XEnergySensor, param="kwhHistories_00", uid="energy_1",
             get_params={"getKwh_00": 2}),
        spec(XEnergySensor, param="kwhHistories_01", uid="energy_2",
             get_params={"getKwh_01": 2}),
    ],  # Sonoff DualR3
    133: [
        # Humidity. ALWAYS 50... NSPanel DOESN'T HAVE HUMIDITY SENSOR
        # https://github.com/AlexxIT/SonoffLAN/issues/751
        Switch1, Switch2, XNSOutdoorTemp, XClimateNS,
        spec(XSensor, param="temperature"),
    ],  # Sonoff NS Panel
    # https://github.com/AlexxIT/SonoffLAN/issues/766
    136: [XLightB05B, RSSI],  # Sonoff B05-BL
    137: [XLightL1, RSSI],
    162: SPEC_3CH,  # https://github.com/AlexxIT/SonoffLAN/issues/659
    165: [Switch1, Switch2, RSSI],  # DualR3 Lite, without power consumption
    174: [XRemoteButton],  # Sonoff R5 (6-key remote)
    177: [XRemoteButton],  # Sonoff S-Mate
    182: [
        Switch1, LED, RSSI,
        spec(XSensor, param="current"),
        spec(XSensor, param="power"),
        spec(XSensor, param="voltage"),
    ],  # Sonoff S40
    1000: [XRemoteButton, Battery],  # zigbee_ON_OFF_SWITCH_1000
    1256: [spec(XSwitch, base="light")],  # ZCL_HA_DEVICEID_ON_OFF_LIGHT
    1770: [
        spec(XSensor100, param="temperature"),
        spec(XSensor100, param="humidity"),
        Battery,
    ],  # ZCL_HA_DEVICEID_TEMPERATURE_SENSOR
    2026: [XZigbeeMotion, Battery],  # ZIGBEE_MOBILE_SENSOR
    3026: [XZigbeeDoor, Battery],  # ZIGBEE_DOOR_AND_WINDOW_SENSOR
    4256: [
        spec(XZigbeeSwitches, channel=0, uid="1"),
        spec(XZigbeeSwitches, channel=1, uid="2"),
        spec(XZigbeeSwitches, channel=2, uid="3"),
        spec(XZigbeeSwitches, channel=3, uid="4"),
    ],
}

# Pow devices sends sensors data via Cloud only in uiActive mode
# UUID, refresh time in seconds, params payload
POW_UI_ACTIVE = {
    32: (3600, {"uiActive": 7200}),
    126: (3600, {"uiActive": {"all": 1, "time": 7200}}),
    182: (0, {"uiActive": 180}),  # maximum for this model
}


def get_spec(device: dict) -> Optional[list]:
    uiid = device["extra"]["uiid"]
    # DualR3 in cover mode
    if uiid in (126, 165) and device["params"].get("workMode") == 2:
        return [XCoverDualR3, RSSI]

    if uiid in DEVICES:
        classes = DEVICES[uiid]
    elif "switch" in device["params"]:
        classes = SPEC_SWITCH
    elif "switches" in device["params"]:
        classes = SPEC_4CH
    else:
        classes = [XUnknown]

    if "device_class" in device:
        classes = get_custom_spec(classes, device["device_class"])

    return classes


def get_custom_spec(classes: list, device_class):
    """Supported device_class formats:
    1. Single channel:
       device_class: light
    2. Multiple channels:
       device_class: [light, fan, switch]
    3. Light with brightness control
       device_class:
         - switch  # entity 1 (channel 1)
         - light: [2, 3]  # entity 2 (channels 2 and 3)
         - fan: 4  # entity 3 (channel 4)
    """
    # 1. single channel
    if isinstance(device_class, str):
        if device_class in DEVICE_CLASS:
            classes = [spec(classes[0], base=device_class)] + classes[1:]

    elif isinstance(device_class, list):
        # remove all default multichannel classes from spec
        base = classes[0].__base__
        classes = [cls for cls in classes if base not in cls.__bases__]

        for i, sub_class in enumerate(device_class):
            # 2. simple multichannel
            if isinstance(sub_class, str):
                classes.append(spec(
                    base, channel=i, uid=str(i + 1), base=sub_class
                ))

            elif isinstance(sub_class, dict):
                sub_class, i = next(iter(sub_class.items()))

                # 3. light with brightness
                if isinstance(i, list) and sub_class == "light":
                    chs = [x - 1 for x in i]
                    uid = ''.join(str(x) for x in i)
                    classes.append(spec(XLightGroup, channels=chs, uid=uid))

                # 4. multichannel
                elif isinstance(i, int):
                    classes.append(spec(
                        base, channel=(i - 1), uid=str(i), base=sub_class
                    ))

    return classes


def set_default_class(device_class: str):
    XSwitch.__bases__ = XSwitches.__bases__ = (
        XEntity, LightEntity if device_class == "light" else SwitchEntity
    )


DIY = {
    # DIY type, UIID, Brand, Model/Name
    "plug": [1, None, "Single Channel DIY"],
    "strip": [4, None, "Multi Channel DIY"],
    "diy_plug": [1, "SONOFF", "MINI DIY"],
    "enhanced_plug": [5, "SONOFF", "POW DIY"],
    "th_plug": [15, "SONOFF", "TH DIY"],
    "rf": [28, "SONOFF", "RFBridge DIY"],
    "fan_light": [34, "SONOFF", "iFan DIY"],
    "light": [44, "SONOFF", "D1 DIY"],
    "multifun_switch": [126, "SONOFF", "DualR3 DIY"],
}


def setup_diy(device: dict) -> dict:
    try:
        uiid, brand, model = DIY[device["diy"]]
        device["name"] = model
        device["brandName"] = brand
        device["extra"] = {"uiid": uiid}
        device["productModel"] = model
    except Exception:
        device["name"] = "Unknown DIY"
        device["extra"] = {"uiid": 0}
        device["productModel"] = device["diy"]
    device["online"] = False
    return device
