import sys
import textwrap

import pytest

from streamdock_core.action import Action
from streamdock_core.action_factory import ActionFactory


@pytest.fixture(autouse=True)
def restore_registry():
    original = dict(ActionFactory._action_types)
    modules = set(sys.modules)
    path = list(sys.path)
    yield
    ActionFactory._action_types = original
    for name in set(sys.modules) - modules:
        del sys.modules[name]
    sys.path[:] = path


class DummyAction(Action):
    def __init__(self, action, context, settings, plugin):
        super().__init__(action, context, settings, plugin)
        self.created = True


class NotAnAction:
    def __init__(self, action, context, settings, plugin):
        pass


class ExplodingAction(Action):
    def __init__(self, action, context, settings, plugin):
        raise RuntimeError('boom')


def write_actions_dir(root, modules):
    """在 root 下生成 actions 包，modules 为 {模块名: 源码}"""
    actions_dir = root / 'actions'
    actions_dir.mkdir()
    (actions_dir / '__init__.py').write_text('')
    for name, source in modules.items():
        (actions_dir / name).write_text(textwrap.dedent(source))
    return str(actions_dir)


ACTION_MODULE = """
    from streamdock_core import Action

    class Demo(Action):
        pass
"""


def test_register_and_create_action_from_dotted_name(plugin):
    ActionFactory.register_action('dummy', DummyAction)

    action = ActionFactory.create_action('com.qxb.plugin.dummy', 'ctx', {'a': 1}, plugin)

    assert isinstance(action, DummyAction)
    assert action.context == 'ctx'
    assert action.settings == {'a': 1}
    assert action.plugin is plugin


def test_create_action_accepts_bare_action_name(plugin):
    ActionFactory.register_action('dummy', DummyAction)

    assert isinstance(ActionFactory.create_action('dummy', 'ctx', {}, plugin), DummyAction)


def test_register_action_overwrites_previous_class(plugin):
    ActionFactory.register_action('dummy', ExplodingAction)
    ActionFactory.register_action('dummy', DummyAction)

    assert isinstance(ActionFactory.create_action('dummy', 'ctx', {}, plugin), DummyAction)


def test_create_action_returns_none_for_unknown_type(plugin):
    assert ActionFactory.create_action('com.qxb.plugin.unknown', 'ctx', {}, plugin) is None


def test_create_action_returns_none_for_empty_action(plugin):
    assert ActionFactory.create_action('', 'ctx', {}, plugin) is None


def test_create_action_returns_none_when_class_is_not_an_action(plugin):
    ActionFactory.register_action('rogue', NotAnAction)

    assert ActionFactory.create_action('rogue', 'ctx', {}, plugin) is None


def test_create_action_returns_none_when_constructor_raises(plugin):
    ActionFactory.register_action('boom', ExplodingAction)

    assert ActionFactory.create_action('boom', 'ctx', {}, plugin) is None


def test_scan_registers_action_subclasses_by_module_name(tmp_path, plugin):
    actions_dir = write_actions_dir(tmp_path, {'demo.py': ACTION_MODULE})

    ActionFactory.scan_and_register_actions(actions_dir)

    assert 'demo' in ActionFactory._action_types
    assert issubclass(ActionFactory._action_types['demo'], Action)
    assert ActionFactory.create_action('com.qxb.x.demo', 'ctx', {}, plugin) is not None


def test_scan_adds_plugin_dir_to_sys_path(tmp_path):
    actions_dir = write_actions_dir(tmp_path, {'demo.py': ACTION_MODULE})

    ActionFactory.scan_and_register_actions(actions_dir)

    assert str(tmp_path) in sys.path


def test_scan_skips_dunder_and_non_python_files(tmp_path):
    actions_dir = write_actions_dir(
        tmp_path,
        {'demo.py': ACTION_MODULE, '__helper__.py': ACTION_MODULE, 'notes.txt': 'x'},
    )
    before = dict(ActionFactory._action_types)

    ActionFactory.scan_and_register_actions(actions_dir)

    assert set(ActionFactory._action_types) - set(before) == {'demo'}


def test_scan_keeps_going_when_a_module_fails_to_import(tmp_path):
    actions_dir = write_actions_dir(
        tmp_path,
        {'broken.py': 'raise RuntimeError("boom")\n', 'demo.py': ACTION_MODULE},
    )

    ActionFactory.scan_and_register_actions(actions_dir)

    assert 'demo' in ActionFactory._action_types
    assert 'broken' not in ActionFactory._action_types


def test_scan_does_nothing_when_actions_dir_is_missing(monkeypatch):
    monkeypatch.setattr(ActionFactory, 'find_actions_dir', classmethod(lambda cls: None))
    before = dict(ActionFactory._action_types)

    ActionFactory.scan_and_register_actions()

    assert ActionFactory._action_types == before


def test_find_actions_dir_detects_flat_layout(tmp_path, monkeypatch):
    (tmp_path / 'actions').mkdir()
    monkeypatch.setattr('streamdock_core.action_factory.bundle_dir', lambda: str(tmp_path))
    monkeypatch.setattr('streamdock_core.action_factory.app_dir', lambda: str(tmp_path))

    assert ActionFactory.find_actions_dir() == str(tmp_path / 'actions')


def test_find_actions_dir_detects_src_layout(tmp_path, monkeypatch):
    (tmp_path / 'src' / 'actions').mkdir(parents=True)
    monkeypatch.setattr('streamdock_core.action_factory.bundle_dir', lambda: str(tmp_path))
    monkeypatch.setattr('streamdock_core.action_factory.app_dir', lambda: str(tmp_path))

    assert ActionFactory.find_actions_dir() == str(tmp_path / 'src' / 'actions')


def test_find_actions_dir_returns_none_without_candidates(tmp_path, monkeypatch):
    monkeypatch.setattr('streamdock_core.action_factory.bundle_dir', lambda: str(tmp_path))
    monkeypatch.setattr('streamdock_core.action_factory.app_dir', lambda: str(tmp_path))

    assert ActionFactory.find_actions_dir() is None
