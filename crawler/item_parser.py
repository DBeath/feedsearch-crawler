import logging
from crawler.response import Response
from crawler.request import Request
from crawler.item import Item
from abc import ABC, abstractmethod


class ItemParser(ABC):
    def __init__(self, spider):
        self.spider = spider
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def parse_item(
        self, request: Request, response: Response, *args, **kwargs
    ) -> Item:
        raise NotImplementedError("Not Implemented")
