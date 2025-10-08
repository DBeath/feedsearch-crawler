import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Queueable:
    item: Any = field(compare=False)
    # Default lowest queue priority is 100 (higher number means lower priority)
    priority: int = 100

    _queue_put_time: float | None = field(compare=False, default=None)
    _queue_get_time: float | None = field(compare=False, default=None)

    def __lt__(self, other: "Queueable") -> bool:
        return self.priority < other.priority

    def __le__(self, other: "Queueable") -> bool:
        return self.priority <= other.priority

    def __gt__(self, other: "Queueable") -> bool:
        return self.priority > other.priority

    def __ge__(self, other: "Queueable") -> bool:
        return self.priority >= other.priority

    def __eq__(self, other: "Queueable") -> bool:
        return self.priority == other.priority

    def get_queue_wait_time(self) -> int:
        """
        Get the time in Milliseconds that this object has been on the queue.

        :return: Queue wait time in Milliseconds as int
        """
        # Only set queue_get_time if not already set, so that the value of this method doesn't change each time
        # it's called.
        if not self._queue_get_time:
            self._queue_get_time = time.monotonic_ns()

        if self._queue_put_time:
            return int(self._queue_get_time - self._queue_put_time) * 1_000_000
        return 0

    def set_queue_put_time(self) -> None:
        """
        Set the time that this object was put onto the queue.
        """
        # Set queue_get_time to None, because this method is called whenever a Queueable is added to the queue
        # and it may be added to a queue multiple times in its life.
        self._queue_get_time = None
        self._queue_put_time = time.monotonic_ns()


@dataclass(slots=True, order=True)
class CallbackResult(Queueable):
    """Dataclass for holding callback results and recording recursion"""

    # CallbackResult priority is high (lower value is higher priority) so that we clear Callbacks off the queue and process them as fast as possible.
    # Otherwise the workers always process Requests and don't often process the Request results.
    priority: int = 1

    callback_recursion: int = field(compare=False, default=0)
