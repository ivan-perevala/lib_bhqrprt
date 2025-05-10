# SPDX-FileCopyrightText: 2020-2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import re
import logging
from logging import Logger, Formatter
from datetime import datetime

__all__ = (
    "setup_logger",
    "teardown_logger",
    "purge_old_logs",
)

_LOG_FILE_EXTENSION = '.txt'
"""Log file format extension (``*.txt``)."""


class _ColoredFormatter(logging.Formatter):
    __RESET = '\x1b[0m'
    __BLUE = '\x1b[1;34m'
    __CYAN = '\x1b[1;36m'
    __PURPLE = '\x1b[1;35m'
    __GRAY = '\x1b[38;20m'
    __YELLOW = '\x1b[33;20m'
    __RED = '\x1b[31;20m'
    __BOLD_RED = '\x1b[31;1m'
    __GREEN = '\x1b[1;32m'

    __format = '{levelname:>8} {name} {funcName:}: {message}'

    _formatters = {
        logging.DEBUG: Formatter(f'{__CYAN}{__format}{__RESET}', style='{'),
        logging.INFO: Formatter(f'{__GREEN}{__format}{__RESET}', style='{'),
        logging.WARNING: Formatter(f'{__YELLOW}{__format}{__RESET}', style='{'),
        logging.ERROR: Formatter(f'{__PURPLE}{__format}{__RESET}', style='{'),
        logging.CRITICAL: Formatter(f'{__RED}{__format}{__RESET}', style='{'),
    }

    def format(self, record: logging.LogRecord) -> str:
        fmt = self._formatters.get(record.levelno)
        assert fmt
        return fmt.format(record)


def setup_logger(*, log: Logger, directory: str) -> None:
    """Logger setup. Log messages would be printed to console and saved to a file in the specified directory.

    :param log: Root logger.
    :type log: logging.Logger
    :param directory: Log files directory.
    :type directory: str
    """

    log_filename = datetime.now().strftime(fr"log %d-%m-%Y %H-%M-%S.%f{_LOG_FILE_EXTENSION}")
    log_filepath = os.path.join(directory, log_filename)

    console_handler = logging.StreamHandler()
    console_formatter = _ColoredFormatter()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    log.addHandler(console_handler)

    file_handler = logging.FileHandler(filename=log_filepath, mode='w', encoding='utf-8')
    file_formatter = logging.Formatter(fmt='{levelname:>8} {asctime} {name} {funcName:}: {message}', style='{')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    log.addHandler(file_handler)

    log.setLevel(logging.DEBUG)


def teardown_logger(*, log: logging.Logger) -> None:
    """Tears down logger setup by removing all handlers from it.

    :param log: Root logger.
    :type log: logging.Logger
    """

    while log.handlers:
        handler = log.handlers[-1]
        handler.close()
        log.removeHandler(handler)


def purge_old_logs(*, directory: str, max_num_logs: int) -> None:
    """Purge old log files in the specified directory according to the maximum number of log files.

    :param directory: Log files directory.
    :type directory: str
    :param max_num_logs: Maximum number of log files in output directory.
    :type max_num_logs: int
    """

    if not max_num_logs:
        return

    pattern = re.compile(r'log (\d{2}-\d{2}-\d{4} \d{2}-\d{2}-\d{2}\.\d{6})\.txt')

    def extract_datetime(filename: str) -> datetime:
        match = re.search(pattern, filename)
        if match:
            datetime_str = match.group(1)
            return datetime.strptime(datetime_str, "%d-%m-%Y %H-%M-%S.%f")
        return datetime.min

    sorted_files = sorted(os.listdir(directory), key=extract_datetime, reverse=True)

    _logs_to_remove = set()

    i = 0
    for filename in sorted_files:
        if os.path.splitext(filename)[1] == _LOG_FILE_EXTENSION:
            if i > max_num_logs:
                _logs_to_remove.add(filename)
            else:
                i += 1

    for filename in _logs_to_remove:
        try:
            os.remove(os.path.join(directory, filename))
        except OSError:
            break
