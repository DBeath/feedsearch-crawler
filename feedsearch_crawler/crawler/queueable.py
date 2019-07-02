import time
from typing import Union
from asyncio import Queue


class Queueable:
    queue_put_time = None
    queue_get_time = None
    # Default lowest queue priority is 10 (higher number means lower priority)
    priority = 10

    def get_queue_wait_time(self) -> Union[float, None]:
        """
        Get the time in Milliseconds that this object has been on the queue.

        :return: Queue wait time in Milliseconds as float
        """
        # Only set queue_get_time if not already set, so that the value of this method doesn't change each time
        # it's called.
        if not self.queue_get_time:
            self.queue_get_time = time.perf_counter()
        if self.queue_put_time:
            return (self.queue_get_time - self.queue_put_time) * 1000
        return None

    def set_queue_put_time(self) -> None:
        """
        Set the time that this object was put onto the queue.
        """
        # Set queue_get_time to None, because this method is called whenever a Queueable is added to the queue
        # and it may be added to a queue multiple times in it's life.
        self.queue_get_time = None
        self.queue_put_time = time.perf_counter()

    def add_to_queue(self, queue: Queue) -> None:
        """
        Add the Queueable to the queue and set the queue put time.

        :param queue: An Queue instance
        """
        self.set_queue_put_time()
        queue.put_nowait(self)

    def __lt__(self, other) -> bool:
        """
        Compare Queueable priority for Queue ordering.
        Lower priority has precedence in the Queue.

        :param other: Another Queueable object
        :return: boolean
        """
        if not isinstance(other, Queueable):
            return True
        return self.priority < other.priority
