import asyncio
import ctypes
from pycaw.pycaw import AudioUtilities
from streamdock_core import Logger
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager
)

VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002

def send_media_key():
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYDOWN, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)

class MusicController:
    def __init__(self):
        self._session = None
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._last_fetch_time = 0   # 用于可选缓存，暂不使用

    def _refresh_session(self):
        """尝试获取当前媒体会话"""
        try:
            sessions = self._loop.run_until_complete(MediaManager.request_async())
            self._session = sessions.get_current_session()
        except Exception as e:
            Logger.warning(f"获取媒体会话失败: {e}")
            self._session = None

    def get_media_info(self):
        # 每次调用都刷新会话，以捕获新打开的媒体应用
        self._refresh_session()

        title = ""
        artist = ""
        if self._session:
            try:
                media_props = self._loop.run_until_complete(
                    self._session.try_get_media_properties_async()
                )
                if media_props:
                    title = media_props.title or ""
                    artist = media_props.artist or ""
            except Exception as e:
                Logger.warning(f"获取媒体属性失败: {e}")

        # 检测播放状态（使用 pycaw）
        playing = False
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.State == 1:  # AudioSessionStateActive
                    playing = True
                    break
        except Exception as e:
            Logger.warning(f"检测音频播放状态失败: {e}")

        status = "PLAYING" if playing else "STOPPED"

        return {
            'title': title,
            'artist': artist,
            'status': status
        }

    def play_pause(self):
        try:
            send_media_key()
            return True
        except Exception as e:
            Logger.error(f"发送媒体按键失败: {e}")
            return False

    def close(self):
        if self._loop:
            self._loop.close()