import logging
from abc import ABC


class Item(ABC):
    def __init__(self, **kwargs):
        self.ignore_item = False
