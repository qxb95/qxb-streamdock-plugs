"""time 插件的 custom action 现在只是共享 demo action 的再导出。"""
from streamdock_core.demo_action import Custom as SharedCustom

from src.actions.custom import Custom


def test_custom_is_the_shared_demo_action():
    assert Custom is SharedCustom


def test_custom_can_be_created_and_sends_demo_events(plugin, ws):
    action = Custom('com.qxb.time.custom', 'ctx-9', {}, plugin)

    assert [e['event'] for e in ws.events] == [
        'setImage', 'setSettings', 'logMessage', 'setTitle', 'showAlert',
    ]
    assert action.settings == {'test': 'test'}
