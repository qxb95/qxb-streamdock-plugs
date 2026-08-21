import os
import sys
import types

from streamdock_core import paths


def test_is_frozen_reflects_sys_flag(monkeypatch):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    assert paths.is_frozen() is False

    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert paths.is_frozen() is True


def test_app_dir_uses_executable_when_frozen(monkeypatch, tmp_path):
    exe = tmp_path / 'plugin.exe'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(exe))

    assert paths.app_dir() == str(tmp_path)


def test_app_dir_uses_main_module_file(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    main = types.SimpleNamespace(__file__=str(tmp_path / 'plugin.py'))
    monkeypatch.setitem(sys.modules, '__main__', main)

    assert paths.app_dir() == str(tmp_path)


def test_app_dir_falls_back_to_cwd(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    monkeypatch.setitem(sys.modules, '__main__', types.SimpleNamespace())
    monkeypatch.chdir(tmp_path)

    assert os.path.realpath(paths.app_dir()) == os.path.realpath(str(tmp_path))


def test_bundle_dir_uses_meipass_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)

    assert paths.bundle_dir() == str(tmp_path)


def test_bundle_dir_matches_app_dir_in_dev(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    monkeypatch.setattr(paths, 'app_dir', lambda: str(tmp_path))

    assert paths.bundle_dir() == str(tmp_path)


def test_find_resource_prefers_external_app_dir(monkeypatch, tmp_path):
    external = tmp_path / 'external'
    bundled = tmp_path / 'bundled'
    (external / 'resources').mkdir(parents=True)
    (bundled / 'resources').mkdir(parents=True)
    (external / 'resources' / 'icon.png').write_bytes(b'x')
    (bundled / 'resources' / 'icon.png').write_bytes(b'y')
    monkeypatch.setattr(paths, 'app_dir', lambda: str(external))
    monkeypatch.setattr(paths, 'bundle_dir', lambda: str(bundled))

    assert paths.find_resource('resources', 'icon.png') == str(external / 'resources' / 'icon.png')


def test_find_resource_falls_back_to_bundle(monkeypatch, tmp_path):
    external = tmp_path / 'external'
    bundled = tmp_path / 'bundled'
    external.mkdir()
    (bundled / 'resources').mkdir(parents=True)
    (bundled / 'resources' / 'icon.png').write_bytes(b'y')
    monkeypatch.setattr(paths, 'app_dir', lambda: str(external))
    monkeypatch.setattr(paths, 'bundle_dir', lambda: str(bundled))

    assert paths.find_resource('resources', 'icon.png') == str(bundled / 'resources' / 'icon.png')


def test_find_resource_returns_bundle_candidate_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, 'app_dir', lambda: str(tmp_path / 'a'))
    monkeypatch.setattr(paths, 'bundle_dir', lambda: str(tmp_path / 'b'))

    assert paths.find_resource('missing.png') == str(tmp_path / 'b' / 'missing.png')


def test_log_dir_is_under_app_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, 'app_dir', lambda: str(tmp_path))

    assert paths.log_dir() == str(tmp_path / 'logs')
