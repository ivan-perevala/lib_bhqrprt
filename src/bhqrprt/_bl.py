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
from typing import Any, Callable, Type

import bpy
from bpy.app.translations import pgettext
from bpy.props import EnumProperty, PointerProperty, IntProperty, StringProperty
from bpy.types import Context, Operator, UILayout, bpy_prop_array, bpy_struct, AddonPreferences, PropertyGroup

from . import _reports

__all__ = (
    "report_and_log",
    "log_execution_helper",
    "log_settings",
    "update_log_setting_changed",
    "get_prop_log_level",
    "template_ui_draw_paths",
    "template_submit_issue",
    "register_reports",
    "unregister_reports",
)

_CUR_DIR = os.path.dirname(__file__)
_ICONS_DIR = os.path.join(_CUR_DIR, "icons")


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


def _get_logger_stream_handler(log: logging.Logger) -> None | logging.StreamHandler:
    for handler in log.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            return handler


def _get_logger_file_handler(log: logging.Logger) -> None | logging.FileHandler:
    for handler in log.root.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler


def get_prop_log_level(log: logging.Logger, *, identifier: str) -> bpy.types.EnumProperty:
    """Property to be used in extension preferences that sets the log level.

    :param log: Current module logger.
    :type log: logging.Logger
    :param identifier: Property identifier (annotation name).
    :type identifier: str
    :return: Property.
    :rtype: `EnumProperty`_
    """

    name_to_level = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
    }  # NOTE: logging.getLevelNamesMapping() is not suitable here, it contains duplicates which are simplier remove here.

    def _update_log_level(self, context: Context):
        value = getattr(self, identifier)

        if stream_handler := _get_logger_stream_handler(log):
            stream_handler.setLevel(value)

        log.log(level=name_to_level[value], msg=f"Log level was set to {value}")

    items = [
        (
            _name,
            _name.capitalize(),
            f"{_name.capitalize()} messages",
            bpy.app.icons.new_triangles_from_file(os.path.join(_ICONS_DIR, f"{_name.lower()}.dat")),
            _level
        ) for _name, _level in name_to_level.items()
    ]

    return EnumProperty(
        items=items,
        default=logging.WARNING,
        update=_update_log_level,
        options={'SKIP_SAVE'},
        translation_context='bhqrprt',
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

    if handler := _get_logger_file_handler(log):
        filepath = handler.baseFilename

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


class _SubmitIssueRegistry:
    BHQRPRT_OT_submit_issue: None | Type[Operator] = None
    icon_value: int = 0

    @classmethod
    def ensure_register_submit_issue_operator(cls, log: logging.Logger):
        if cls.BHQRPRT_OT_submit_issue:
            return

        name = log.name.replace('.', '_')

        handler = _get_logger_file_handler(log)
        if handler:

            def _execute(self, context: Context):
                bpy.ops.wm.url_open('EXEC_DEFAULT', url=self.url)
                bpy.ops.wm.path_open('EXEC_DEFAULT', filepath=handler.baseFilename)
                return {'FINISHED'}

            cls.BHQRPRT_OT_submit_issue = type(
                f"BHQRPRT_OT_{name}_submit_issue",
                (Operator,),
                dict(
                    bl_idname=f"bhqrprt.{name}",
                    bl_label="Submit Issue",
                    bl_descriprion="Open issues page in browser and current log file",
                    __annotations__=dict(url=StringProperty(options={'HIDDEN', 'SKIP_SAVE'},)),
                    execute=_execute
                )
            )

            bpy.utils.register_class(cls.BHQRPRT_OT_submit_issue)

            cls.icon_value = bpy.app.icons.new_triangles_from_file(os.path.join(_ICONS_DIR, "issue.dat"))

    @classmethod
    def unregister_submit_issue_operator(cls):
        if cls.BHQRPRT_OT_submit_issue:
            bpy.utils.unregister_class(cls.BHQRPRT_OT_submit_issue)
            cls.BHQRPRT_OT_submit_issue = None


def template_submit_issue(layout: UILayout, url: str):
    col = layout.column(align=False)
    col.alert = True
    col.scale_y = 1.5

    props = col.operator(
        operator=_SubmitIssueRegistry.BHQRPRT_OT_submit_issue.bl_idname,
        icon_value=_SubmitIssueRegistry.icon_value
    )
    props.url = url


class _LogSettingsRegistry:
    BHQRPRT_log_settings: None | Type[PropertyGroup] = None

    @classmethod
    def register_log_settings_class(cls, log: logging.Logger):
        if cls.BHQRPRT_log_settings:
            bpy.utils.unregister_class(cls.BHQRPRT_log_settings)

        name = log.name.replace('.', '_')

        cls.BHQRPRT_log_settings = type(
            f"BHQRPRT_{name}_log_settings",
            (PropertyGroup,),
            {
                "__annotations__": {
                    "log_level": get_prop_log_level(log, identifier="log_level"),
                    "max_num_logs": IntProperty(
                        min=1,
                        soft_min=5,
                        soft_max=100,
                        default=30,
                        options={'SKIP_SAVE'},
                        name="Max Number of Log Files",
                        description=(
                            "Max number of log files in logs directory. "
                            "Older files would be deleted if number of log files is greater than this value"
                        )
                    )
                }
            }
        )
        bpy.utils.register_class(cls.BHQRPRT_log_settings)

    @classmethod
    def unregister_log_settings_class(cls):
        if cls.BHQRPRT_log_settings:
            bpy.utils.unregister_class(cls.BHQRPRT_log_settings)
            cls.BHQRPRT_log_settings = None


def register_reports(log: logging.Logger, pref_cls: Type[AddonPreferences], directory: str):
    def _draw_log_settings_helper(draw_func):
        def _draw_wrapper(self, context: Context):
            draw_func(context)

            assert context.preferences

            if context.preferences.view.show_developer_ui:
                layout: UILayout = self.layout
                col = layout.column(align=True)

                idname = f"bhqrprt_{pref_cls.__name__.lower()}_reports"
                header, panel = col.panel(idname, default_closed=True)
                header.label(
                    text="Reports",
                    icon_value=header.enum_item_icon(self.bhqrprt, "log_level", self.bhqrprt.log_level)
                )
                if panel:
                    row = panel.row(align=True)
                    row.prop(self.bhqrprt, "log_level")
                    panel.prop(self.bhqrprt, "max_num_logs")
                    template_ui_draw_paths(log, panel, msgctxt="")

        return _draw_wrapper

    def _register_helper(register):
        def _register():
            _reports.setup_logger(log=log, directory=directory)

            _LogSettingsRegistry.register_log_settings_class(log)
            pref_cls.__annotations__['bhqrprt'] = PointerProperty(type=_LogSettingsRegistry.BHQRPRT_log_settings)

            register()

            pref = bpy.context.preferences
            assert pref
            addon = pref.addons.get(pref_cls.bl_idname, None)
            if addon:
                addon_pref = addon.preferences
                if addon_pref:
                    setattr(pref_cls, "draw", _draw_log_settings_helper(getattr(addon_pref, "draw")))

                    if value := addon_pref.bhqrprt.log_level:
                        if stream_handler := _get_logger_stream_handler(log):
                            stream_handler.setLevel(value)

                        _reports.purge_old_logs(directory=directory, max_num_logs=addon_pref.bhqrprt.max_num_logs)

                    _SubmitIssueRegistry.ensure_register_submit_issue_operator(log)

        return _register

    return _register_helper


def unregister_reports(unregister):
    def _unregister():
        unregister()
        _LogSettingsRegistry.unregister_log_settings_class()

    return _unregister
