import time

from feedsearch_crawler.crawler.queueable import CallbackResult, Queueable


# Test Initialization
def test_initialization() -> None:
    queueable = Queueable(item="test")
    assert queueable.item == "test"
    assert queueable.priority == 100
    assert queueable._queue_put_time is None
    assert queueable._queue_get_time is None


# Test Queue Put Time
def test_set_queue_put_time() -> None:
    queueable = Queueable(item="test")
    queueable.set_queue_put_time()
    assert queueable._queue_put_time is not None
    assert queueable._queue_get_time is None


# Test Queue Wait Time
def test_get_queue_wait_time() -> None:
    queueable = Queueable(item="test")
    queueable.set_queue_put_time()
    time.sleep(0.01)  # Sleep for 10 milliseconds
    wait_time = queueable.get_queue_wait_time()
    assert wait_time >= 10_000_000  # Check if wait time is at least 10 milliseconds
    assert queueable._queue_get_time is not None
    assert queueable._queue_get_time is not None


# Test Queueable Ordering
def test_queueable_ordering() -> None:
    queueable1 = Queueable(item="test1", priority=1)
    queueable2 = Queueable(item="test2", priority=2)
    queueable3 = Queueable(item="test3", priority=3)

    assert queueable1 < queueable2 < queueable3
    assert queueable3 > queueable2 > queueable1
    assert queueable1 <= queueable2 <= queueable3
    assert queueable3 >= queueable2 >= queueable1
    assert queueable1 != queueable2
    assert queueable1 == queueable1
    assert queueable2 == queueable2
    assert queueable3 == queueable3
    assert queueable1 <= queueable1
    assert queueable1 >= queueable1
    assert queueable2 <= queueable2
    assert queueable2 >= queueable2
    assert queueable3 <= queueable3
    assert queueable3 >= queueable3
    assert queueable1 == queueable1
    assert queueable2 == queueable2
    assert queueable3 == queueable3
    assert queueable1 != queueable2
    assert queueable1 != queueable3
    assert queueable2 != queueable3
    assert queueable3 != queueable1
    assert queueable3 != queueable2
    assert queueable2 != queueable1
    assert queueable2 != queueable3
    assert queueable1 != queueable3
    assert queueable3 != queueable1
    assert queueable2 != queueable3
    assert queueable3 != queueable2
    assert queueable1 != queueable2
    assert queueable2 != queueable1
    assert queueable1 < queueable2
    assert queueable2 < queueable3
    assert queueable1 < queueable3
    assert queueable3 > queueable2
    assert queueable2 > queueable1
    assert queueable3 > queueable1
    assert queueable1 <= queueable2
    assert queueable2 <= queueable3
    assert queueable1 <= queueable3
    assert queueable3 >= queueable2
    assert queueable2 >= queueable1
    assert queueable3 >= queueable1


def test_callbackresult_init() -> None:
    result1 = CallbackResult(item="test1")
    assert result1.item == "test1"
    assert result1.priority == 1
    assert result1.callback_recursion == 0
    assert result1._queue_put_time is None
    assert result1._queue_get_time is None
