import logging

import pytest

from core.logger import Logger


@pytest.fixture
def records(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


def test_logger_is_singleton():
    assert Logger() is Logger()
    assert Logger.get_instance() is Logger()


def test_get_logger_returns_configured_logger():
    logger = Logger.get_logger()

    assert isinstance(logger, logging.Logger)
    assert logger.name == 'StreamDock'
    assert logger.level == logging.INFO
    assert logger.handlers, '应至少配置一个 handler'


def test_setup_logger_is_idempotent():
    handler_count = len(Logger.get_logger().handlers)

    Logger._setup_logger()

    assert len(Logger.get_logger().handlers) == handler_count


@pytest.mark.parametrize(
    'method, level',
    [
        (Logger.info, 'INFO'),
        (Logger.error, 'ERROR'),
        (Logger.warning, 'WARNING'),
    ],
)
def test_level_helpers_emit_records(records, method, level):
    method('消息内容')

    assert [(r.levelname, r.message) for r in records.records] == [(level, '消息内容')]


def test_debug_is_filtered_by_logger_level(records):
    Logger.debug('调试信息')

    assert records.records == [], 'logger 级别为 INFO，debug 不应被记录'


def test_get_logger_recreates_logger_when_reset():
    original = Logger._logger
    handlers = list(original.handlers)
    Logger._logger = None
    try:
        logger = Logger.get_logger()

        assert logger.name == 'StreamDock'
        assert logger.handlers
    finally:
        Logger._logger = original
        original.handlers = handlers
