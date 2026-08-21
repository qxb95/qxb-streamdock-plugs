import threading

from streamdock_core.timer import Timer


def test_set_interval_converts_milliseconds_to_seconds():
    timer = Timer()
    timer.set_interval('a', 2500, lambda: None)

    assert timer._intervals['a']['delay'] == 2.5


def test_set_interval_overwrites_existing_uuid():
    timer = Timer()
    first, second = lambda: None, lambda: None
    timer.set_interval('a', 1000, first)
    timer.set_interval('a', 1000, second)

    assert len(timer._intervals) == 1
    assert timer._intervals['a']['callback'] is second


def test_clear_interval_removes_entry():
    timer = Timer()
    timer.set_interval('a', 1000, lambda: None)
    timer.set_interval('b', 1000, lambda: None)

    timer.clear_interval('a')

    assert set(timer._intervals) == {'b'}


def test_clear_interval_is_noop_for_unknown_uuid():
    timer = Timer()
    timer.clear_interval('missing')

    assert timer._intervals == {}


def test_background_thread_invokes_callback():
    timer = Timer()
    called = threading.Event()
    timer.set_interval('tick', 100, called.set)

    assert called.wait(3), '定时器回调应在后台线程中被调用'

    timer.clear_interval('tick')


def test_cleared_interval_stops_firing():
    timer = Timer()
    calls = []
    timer.set_interval('tick', 100, lambda: calls.append(1))

    deadline = threading.Event()
    deadline.wait(0.5)
    timer.clear_interval('tick')
    count_after_clear = len(calls)
    deadline.wait(0.5)

    assert count_after_clear > 0
    assert len(calls) == count_after_clear


def test_timer_thread_is_daemon():
    timer = Timer()

    assert timer._thread.daemon is True
    assert timer._thread.is_alive()


def test_callback_exception_does_not_kill_timer_thread():
    timer = Timer()
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError('boom')

    timer.set_interval('tick', 100, boom)
    deadline = threading.Event()
    deadline.wait(0.5)
    timer.clear_interval('tick')

    assert len(calls) > 1, '回调抛异常后定时器线程应继续运行'
    assert timer._thread.is_alive()
