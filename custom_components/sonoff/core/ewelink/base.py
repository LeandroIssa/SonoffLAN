import time
from typing import Callable, Dict, List, Optional, TypedDict

from aiohttp import ClientSession

SIGNAL_CONNECTED = "connected"
SIGNAL_UPDATE = "update"


class XDevice(TypedDict, total=False):
    deviceid: str
    extra: dict
    name: str
    params: dict

    brandName: Optional[str]
    productModel: Optional[str]

    online: Optional[bool]  # required for cloud
    apikey: Optional[str]  # required for cloud

    host: Optional[str]  # required for local
    devicekey: Optional[str]  # required for encrypted local devices (not DIY)

    params_bulk: Optional[dict]  # helper for send_bulk commands
    pow_ts: Optional[int]  # required for pow devices with cloud connection


class XRegistryBase:
    dispatcher: Dict[str, List[Callable]] = None
    _sequence: int = 0

    def __init__(self, session: ClientSession):
        self.dispatcher = {}
        self.session = session

    @staticmethod
    def sequence() -> str:
        """Return sequnce counter in ms. Always unique."""
        t = int(time.time()) * 1000
        if t > XRegistryBase._sequence:
            XRegistryBase._sequence = t
        else:
            XRegistryBase._sequence += 1
        return str(XRegistryBase._sequence)

    def dispatcher_connect(self, signal: str, target: Callable):
        targets = self.dispatcher.setdefault(signal, [])
        if target not in targets:
            targets.append(target)

    def dispatcher_send(self, signal: str, *args, **kwargs):
        if not self.dispatcher.get(signal):
            return
        for handler in self.dispatcher[signal]:
            handler(*args, **kwargs)
