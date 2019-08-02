from attr import attrs, attrib, Factory
import collections
import traceback
from typing import *


@attrs(slots=True, auto_attribs=True)
class EventEmitter:
    """
    """
    events: Dict[str, Callable[..., None]] = Factory(lambda: collections.defaultdict(list))

    def on(self, name: str, cb: Callable[..., None]) -> None:
        self.events[name].append(cb)

    def off(self, name, cb: Callable[..., None]) -> None:
        self.events[name].remove(cb)

    def emit(self, name, *args, **kwds) -> None:
        for cb in self.events[name]:
            try:
                cb(*args, **kwds)
            except:
                # todo; we should throw a warning
                traceback.print_exc()
                pass


__all__ = ['EventEmitter']
