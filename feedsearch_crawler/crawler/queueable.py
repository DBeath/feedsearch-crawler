import time
from typing import Union


class Queueable:
    queue_put_time = None
    queue_get_time = None

    def get_queue_wait_time(self) -> Union[float, None]:
        """
        Get the time in Milliseconds that this object has been on the queue.

        :return: Queue wait time in Milliseconds as float
        """
        if not self.queue_get_time:
            self.queue_get_time = time.perf_counter()
        if self.queue_put_time:
            return (self.queue_get_time - self.queue_put_time) * 1000
        return None

    def set_queue_put_time(self) -> None:
        """
        Set the time that this object was put onto the queue.
        """
        self.queue_put_time = time.perf_counter()
