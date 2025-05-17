# SPDX-FileCopyrightText: 2020-2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Python package designed to streamline the process of logging for both Python applications and Blender
extensions development. It provides advanced logging features such as automatic log file management, colored console
outputs, and a specialized API for seamless integration with Blender's operator execution processes.
"""

from __future__ import annotations

from typing import Any

HAS_BPY: bool = False
"""If ``bpy`` module is available. Most of functionality of this module depends on it.
Value is constant, and evaluated at import time.
"""

try:
    import bpy as _bpy_check
except ImportError:
    HAS_BPY = False
else:
    HAS_BPY = hasattr(_bpy_check, "context")  # `fake-bpy-module` is just stubs.
    del _bpy_check

if __debug__:
    def __reload_submodules(lc: dict[str, Any]) -> None:
        import importlib

        if "_reports" in lc:
            importlib.reload(_reports)
        if "_bl" in lc:
            importlib.reload(_bl)

    __reload_submodules(locals())
    del __reload_submodules

from . import _reports
from . _reports import purge_old_logs, setup_logger, teardown_logger

if HAS_BPY:
    from . import _bl
    from . _bl import register_reports, unregister_reports, template_submit_issue, log_bpy_struct_properties, report_and_log, log_execution_helper, update_log_setting_changed, operator_report

__all__ = (
    "HAS_BPY",

    # file://./_reports.py
    "purge_old_logs",
    "setup_logger",
    "teardown_logger",

    # file://./_bl.py
    "register_reports",
    "unregister_reports",
    "template_submit_issue",
    "log_bpy_struct_properties",
    "report_and_log",
    "log_execution_helper",
    "operator_report",
    "update_log_setting_changed",
)
