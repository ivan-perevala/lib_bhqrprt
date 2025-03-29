# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import logging
import tempfile
import bhqrprt

tmpdir: tempfile.TemporaryDirectory


def setup_module():
    global tmpdir
    tmpdir = tempfile.TemporaryDirectory()

    bhqrprt.setup_logger(directory=tmpdir.name)


def teardown_module():
    global tmpdir

    bhqrprt.teardown_logger()

    tmpdir.cleanup()

def test_a(caplog):
    log = logging.getLogger()

    with caplog.at_level(logging.DEBUG):
        log.debug("Debug test message")
        assert caplog.records[-1].message == "Debug test message"

    with caplog.at_level(logging.INFO):
        log.info("Info test message")
        assert caplog.records[-1].message == "Info test message"

    with caplog.at_level(logging.WARNING):
        log.warning("Warning test message")
        assert caplog.records[-1].message == "Warning test message"

    with caplog.at_level(logging.ERROR):
        log.error("Error test message")
        assert caplog.records[-1].message == "Error test message"
