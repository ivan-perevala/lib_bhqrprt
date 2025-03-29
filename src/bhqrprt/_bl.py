# SPDX-FileCopyrightText: 2020-2024 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import inspect
import logging
import os
import pprint
import textwrap
import time
from typing import Any, Callable

import bpy
from bpy.app.translations import pgettext
from bpy.props import EnumProperty
from bpy.types import Context, Operator, UILayout, bpy_prop_array, bpy_struct

__all__ = (
    "report_and_log",
    "log_execution_helper",
    "log_settings",
    "update_log_setting_changed",
    "get_prop_log_level",
    "template_ui_draw_paths",
)


def report_and_log(
    log: logging.Logger,
    operator: Operator,
    *,
    level: int,
    message: str,
    **msg_kwargs: dict[str, Any]
) -> None:
    """Allows to make a report message and log simultaneously. For internationalization, the message will be
    translated and reported using the operator's translation context.

    :param log: Logger of the current module.
    :type log: logging.Logger
    :param operator: Current operator.
    :type operator: `Operator`_
    :param level: Log level.
    :type level: int
    :param message: Message format.
    :type message: str
    """

    log.log(level=level, msg=message.format(**msg_kwargs))

    report_message = pgettext(msgid=message, msgctxt=operator.bl_translation_context).format(**msg_kwargs)

    match level:
        case logging.DEBUG | logging.INFO:
            operator.report(type={'INFO'}, message=report_message)
        case logging.WARNING:
            operator.report(type={'WARNING'}, message=report_message)
        case logging.ERROR | logging.CRITICAL:
            operator.report(type={'ERROR'}, message=report_message)


def _filter_paths_from_keywords(*, keywords: dict[str, Any]) -> dict[str, Any]:
    _str_hidden = "(hidden for security reasons)"
    arg_filepath = keywords.get("filepath", None)
    arg_directory = keywords.get("directory", None)
    arg_filename = keywords.get("filename", None)

    if arg_filepath is not None and arg_filepath:
        if os.path.exists(bpy.path.abspath(arg_filepath)):
            filepath_fmt = f"Existing File Path {_str_hidden}"
        else:
            filepath_fmt = f"Missing File Path {_str_hidden}"

        keywords["filepath"] = filepath_fmt

    if arg_directory is not None and arg_directory:
        if os.path.isdir(bpy.path.abspath(arg_directory)):
            directory_fmt = f"Existing Directory Path {_str_hidden}"
        else:
            directory_fmt = f"Missing Directory Path {_str_hidden}"

        keywords["directory"] = directory_fmt

    if arg_filename is not None and arg_filename:
        keywords["filename"] = f"Some Filename {_str_hidden}"

    return keywords


def log_execution_helper(
        ot_execute_method: Callable[[Operator, Context], set[int | str]]
) -> Callable[[Operator, Context], set[int | str]]:
    """Operator's execution helper decorator. It will first print which operator and with which options is being called,
    then call the operator's method and print the execution result in the log.

    :param ot_execute_method: Current operator's execution method.
    :type ot_execute_method: Callable[[Operator, Context], set[int | str]]
    :return: Operator's execution result.
    :rtype: Callable[[Operator, Context], set[int | str]]
    """

    log = logging.getLogger(inspect.stack()[2].filename)

    def execute(operator, context):
        props = operator.as_keywords()

        if props:
            props_fmt = textwrap.indent(
                pprint.pformat(
                    _filter_paths_from_keywords(keywords=props),
                    indent=4,
                    compact=False),
                prefix=' ' * 40
            )
            log.debug(f"\"{operator.bl_label}\" execution begin with properties:\n{props_fmt}")
        else:
            log.debug(f"\"{operator.bl_label}\" execution begin")

        dt = time.time()

        ret = ot_execute_method(operator, context)

        log.debug(f"\"{operator.bl_label}\" execution ended as {ret} in {time.time() - dt:.6f} second(s)")

        return ret

    return execute


def _get_value(*, item: object, identifier: str):
    return getattr(item, identifier, "(readonly)")


def _format_setting_value(*, value: bool | int | float | str | bpy_prop_array) -> str:
    if isinstance(value, float):
        return '%.6f' % value
    elif isinstance(value, str):
        if '\n' in value:
            return value.split('\n')[0][:-1] + " ... (multi-lined string skipped)"
        elif len(value) > 50:
            return value[:51] + " ... (long string skipped)"
    elif isinstance(value, bpy_prop_array):
        return ", ".join((_format_setting_value(value=_) for _ in value))

    return str(value)


def log_settings(log: logging.Logger, *, item: bpy_struct) -> None:
    """Logs structure properties. It can be used, for example, to log the settings with which the extension was started.

    :param log: Current module logger.
    :type log: logging.Logger
    :param item: Structure.
    :type item: `bpy_struct`_
    """
    for prop in item.bl_rna.properties:
        identifier = prop.identifier
        if identifier != 'rna_type':
            value = _get_value(item=item, identifier=identifier)
            value_fmt = _format_setting_value(value=value)

            log.debug("{identifier}: {value_fmt}".format(identifier=identifier, value_fmt=value_fmt))

            if type(prop.rna_type) == bpy.types.PointerProperty:
                log_settings(log, item=getattr(item, prop.identifier))


def update_log_setting_changed(log: logging.Logger, identifier: str) -> Callable[[bpy_struct, Context], None]:
    """Method for updating properties. If the property has been updated, it must be logged. Commonly used for
    logging preferences and scene changes.

    :param log: Current module logger.
    :type log: logging.Logger
    :param identifier: String identifier of the property in the class.
    :type identifier: str
    :return: Callable method to be used property update method.
    :rtype: Callable[[bpy_struct, Context], None]
    """

    def _log_setting_changed(self, _context: Context):
        value = _get_value(item=self, identifier=identifier)
        value_fmt = _format_setting_value(value=value)
        log.debug(f"Setting updated \'{self.bl_rna.name}.{identifier}\': {value_fmt}")

    return _log_setting_changed


def get_prop_log_level(log: logging.Logger, *, identifier: str) -> bpy.types.EnumProperty:
    """Property to be used in extension preferences that sets the log level.

    :param log: Current module logger.
    :type log: logging.Logger
    :param identifier: Property identifier (annotation name).
    :type identifier: str
    :return: Property.
    :rtype: `EnumProperty`_
    """
    _update_log_log_level = update_log_setting_changed(log, identifier=identifier)

    def _update_log_level(self, context: Context):
        for handle in log.root.handlers:
            if type(handle) == logging.StreamHandler:
                handle.setLevel(getattr(self, identifier))

        _update_log_log_level(self, context)

    return EnumProperty(
        items=(
            (
                logging.getLevelName(logging.DEBUG),
                "Debug",
                "Debug messages (low priority)",
                0,
                logging.DEBUG,
            ),
            (
                logging.getLevelName(logging.INFO),
                "Info",
                "Informational messages",
                0,
                logging.INFO,
            ),
            (
                logging.getLevelName(logging.WARNING),
                "Warning",
                "Warning messages (medium priority)",
                0,
                logging.WARNING,
            ),
            (
                logging.getLevelName(logging.ERROR),
                "Error",
                "Error messages (high priority)",
                0,
                logging.ERROR,
            ),
            (
                logging.getLevelName(logging.CRITICAL),
                "Critical",
                "Critical error messages",
                0,
                logging.CRITICAL,
            ),
        ),  # type: ignore
        default=logging.getLevelName(logging.WARNING),
        update=_update_log_level,
        options={'SKIP_SAVE'},
        translation_context='BHQAB_Preferences',
        name="Log Level",
        description=(
            "The level of the log that will be output to the console. For log to file, this level value will "
            "not change"
        ),
    )


def template_ui_draw_paths(log: logging.Logger, layout: UILayout, *, msgctxt: str) -> None:
    """Template for displaying operators that open the path to the log directory and the current log.

    :param log: Current module logger.
    :type log: logging.Logger
    :param layout: Current UI layout.
    :type layout: `UILayout`_
    :param msgctxt: Translation context for file path display.
    :type msgctxt: str
    """

    filepath: None | str = None

    for handler in log.root.handlers:
        if isinstance(handler, logging.FileHandler):
            filepath = handler.baseFilename

    if filepath:
        directory, filename = os.path.split(filepath)

        layout.operator(
            operator="wm.path_open",
            text="Open Log Files Directory",
            text_ctxt=msgctxt,
        ).filepath = directory

        layout.operator(
            operator="wm.path_open",
            text=pgettext("Open Log: \"{filename}\"", msgctxt=msgctxt).format(filename=filename),
        ).filepath = filepath
