import time


class Queueable:
    _queue_put_time = None
    _queue_get_time = None
    # Default lowest queue priority is 100 (higher number means lower priority)
    priority = 100

    def get_queue_wait_time(self) -> int:
        """
        Get the time in Milliseconds that this object has been on the queue.

        :return: Queue wait time in Milliseconds as int
        """
        # Only set queue_get_time if not already set, so that the value of this method doesn't change each time
        # it's called.
        if not self._queue_get_time:
            self._queue_get_time = time.perf_counter()

        if self._queue_put_time:
            return int(self._queue_get_time - self._queue_put_time) * 1000
        return 0

    def set_queue_put_time(self) -> None:
        """
        Set the time that this object was put onto the queue.
        """
        # Set queue_get_time to None, because this method is called whenever a Queueable is added to the queue
        # and it may be added to a queue multiple times in its life.
        self._queue_get_time = None
        self._queue_put_time = time.perf_counter()

    def __lt__(self, __o: object) -> bool:
        """
        Compare Queueable priority for Queue ordering.
        Lower priority has precedence in the Queue.

        :param other: Another Queueable object
        :return: boolean
        """
        if not isinstance(__o, Queueable):
            return True
        elif self.priority == __o.priority:
            return self.get_queue_wait_time() < __o.get_queue_wait_time()
        else:
            return self.priority < __o.priority

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Queueable):
            return False
        elif self.priority != __o.priority:
            return self.get_queue_wait_time() == __o.get_queue_wait_time()
        else:
            return True
