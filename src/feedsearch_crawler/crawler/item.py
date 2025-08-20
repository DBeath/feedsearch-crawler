from abc import ABC
from typing import Any, Dict


class Item(ABC):
    ignore_item = False

    def __init__(self, **kwargs: Dict[str, Any]) -> None:
        for k in kwargs.keys():
            if hasattr(self, k):
                self.__setattr__(k, kwargs[k])
