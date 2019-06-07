import logging
from abc import ABC


class Item(ABC):
    def __init__(self):
        self.ignore_item = False
        self.logger = logging.getLogger(__name__)
