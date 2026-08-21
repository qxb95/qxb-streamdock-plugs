import pytest

from src.core.action import Action
from src.core.action_factory import ActionFactory


@pytest.fixture(autouse=True)
def restore_registry():
    original = dict(ActionFactory._action_types)
    yield
    ActionFactory._action_types = original


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


def test_scan_registers_bundled_actions():
    assert set(ActionFactory._action_types) >= {'time', 'custom'}
    assert all(issubclass(cls, Action) for cls in ActionFactory._action_types.values())


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


def test_create_action_returns_none_when_class_is_not_an_action(plugin):
    ActionFactory.register_action('rogue', NotAnAction)

    assert ActionFactory.create_action('rogue', 'ctx', {}, plugin) is None


def test_create_action_returns_none_when_constructor_raises(plugin):
    ActionFactory.register_action('boom', ExplodingAction)

    assert ActionFactory.create_action('boom', 'ctx', {}, plugin) is None


def test_scan_logs_error_when_actions_dir_missing(monkeypatch):
    monkeypatch.setattr('src.core.action_factory.os.path.exists', lambda path: False)
    before = dict(ActionFactory._action_types)

    ActionFactory.scan_and_register_actions()

    assert ActionFactory._action_types == before
