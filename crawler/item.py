import logging


class Item:
    def __init__(self):
        self.ignore_item = False
        self.logger = logging.getLogger(__name__)
