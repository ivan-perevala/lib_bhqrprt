# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import logging
import tempfile
import bhqrprt


def test_logger_handlers(caplog):
    with tempfile.TemporaryDirectory() as tmpdir:
        log = logging.getLogger("test_logger_handlers")

        ##############
        # Setup Logger
        ##############

        bhqrprt.setup_logger(name=log.name, directory=tmpdir)

        # Should be 2 handlers.
        assert len(log.handlers) == 2

        ###########
        # Tear Down
        ###########

        bhqrprt.teardown_logger(name=log.name)

        # Should be no handlers.
        assert len(log.handlers) == 0
