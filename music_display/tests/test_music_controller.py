import pytest

from core import music_controller
from core.music_controller import MusicController

from conftest import FakeAudioUtilities, FakeMediaManager


class FakeMediaProperties:
    def __init__(self, title, artist):
        self.title = title
        self.artist = artist


class FakeSession:
    def __init__(self, properties=None, raises=None):
        self._properties = properties
        self._raises = raises

    async def try_get_media_properties_async(self):
        if self._raises is not None:
            raise self._raises
        return self._properties


class FakeAudioSession:
    def __init__(self, state):
        self.State = state


@pytest.fixture
def controller():
    instance = MusicController()
    yield instance
    instance.close()


def test_get_media_info_reports_playing_track(controller):
    FakeMediaManager.session = FakeSession(FakeMediaProperties('青花瓷', '周杰伦'))
    FakeAudioUtilities.sessions = [FakeAudioSession(0), FakeAudioSession(1)]

    assert controller.get_media_info() == {
        'title': '青花瓷',
        'artist': '周杰伦',
        'status': 'PLAYING',
    }


def test_get_media_info_reports_stopped_when_no_active_audio_session(controller):
    FakeMediaManager.session = FakeSession(FakeMediaProperties('青花瓷', '周杰伦'))
    FakeAudioUtilities.sessions = [FakeAudioSession(0)]

    assert controller.get_media_info()['status'] == 'STOPPED'


def test_get_media_info_without_media_session(controller):
    assert controller.get_media_info() == {'title': '', 'artist': '', 'status': 'STOPPED'}
    assert controller._session is None


def test_get_media_info_when_session_manager_fails(controller):
    FakeMediaManager.raises = OSError('no media manager')

    assert controller.get_media_info()['title'] == ''
    assert controller._session is None


def test_get_media_info_when_properties_lookup_fails(controller):
    FakeMediaManager.session = FakeSession(raises=OSError('denied'))

    assert controller.get_media_info() == {'title': '', 'artist': '', 'status': 'STOPPED'}


def test_get_media_info_when_properties_are_missing(controller):
    FakeMediaManager.session = FakeSession(None)

    assert controller.get_media_info()['title'] == ''


def test_get_media_info_normalizes_none_fields(controller):
    FakeMediaManager.session = FakeSession(FakeMediaProperties(None, None))

    assert controller.get_media_info() == {'title': '', 'artist': '', 'status': 'STOPPED'}


def test_get_media_info_when_audio_session_enumeration_fails(controller):
    FakeMediaManager.session = FakeSession(FakeMediaProperties('t', 'a'))
    FakeAudioUtilities.raises = OSError('pycaw failure')

    assert controller.get_media_info()['status'] == 'STOPPED'


def test_get_media_info_refreshes_session_on_every_call(controller):
    calls = []

    class CountingManager(FakeMediaManager):
        @classmethod
        async def request_async(cls):
            calls.append(1)
            return cls

    original = music_controller.MediaManager
    music_controller.MediaManager = CountingManager
    try:
        controller.get_media_info()
        controller.get_media_info()
    finally:
        music_controller.MediaManager = original

    assert len(calls) == 2


def test_send_media_key_emits_key_down_and_up(monkeypatch):
    events = []

    class FakeUser32:
        def keybd_event(self, key, scan, flags, extra):
            events.append((key, flags))

    class FakeWindll:
        user32 = FakeUser32()

    monkeypatch.setattr(music_controller.ctypes, 'windll', FakeWindll(), raising=False)

    music_controller.send_media_key()

    assert events == [
        (music_controller.VK_MEDIA_PLAY_PAUSE, music_controller.KEYEVENTF_KEYDOWN),
        (music_controller.VK_MEDIA_PLAY_PAUSE, music_controller.KEYEVENTF_KEYUP),
    ]


def test_play_pause_returns_true_when_key_is_sent(controller, monkeypatch):
    monkeypatch.setattr(music_controller, 'send_media_key', lambda: None)

    assert controller.play_pause() is True


def test_play_pause_returns_false_when_key_sending_fails(controller, monkeypatch):
    def boom():
        raise OSError('no windll')

    monkeypatch.setattr(music_controller, 'send_media_key', boom)

    assert controller.play_pause() is False


def test_close_closes_event_loop():
    controller = MusicController()

    controller.close()

    assert controller._loop.is_closed()
