from abc import ABC


class Item(ABC):
    ignore_item = False

    def __init__(self, **kwargs):
        for k in kwargs.keys():
            if hasattr(self, k):
                self.__setattr__(k, kwargs[k])
