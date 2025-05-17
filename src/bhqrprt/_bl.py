# SPDX-FileCopyrightText: 2020-2024 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# ---
# NOTE: At this moment, there is Blender stubs which would work perfectly. Thats why most of static type checks should
# be just ignored:
#
# type: ignore
# ---

from __future__ import annotations

import inspect
import logging
import os
import pprint
import textwrap
import time
from typing import Any, Callable, Type
from logging import Logger

import bpy
from bpy.app.translations import pgettext
from bpy.props import EnumProperty, PointerProperty, IntProperty, StringProperty
from bpy.types import Context, Operator, UILayout, bpy_prop_array, bpy_struct, AddonPreferences, PropertyGroup

from . import _reports

__all__ = (
    "register_reports",
    "unregister_reports",
    "template_submit_issue",
    "report_and_log",
    "log_execution_helper",
    "update_log_setting_changed",
)

_CUR_DIR = os.path.dirname(__file__)
_ICONS_DIR = os.path.join(_CUR_DIR, "icons")


def _eval_name(name: str):
    name_eval = name.replace('.', '_')

    if len(name_eval) > 30:
        name_eval = name_eval[:30]

    return name_eval


class _LogSettingsRegistry:
    BHQRPRT_log_settings: None | Type[PropertyGroup] = None

    @staticmethod
    def _get_prop_log_level(log: Logger, *, identifier: str) -> bpy.types.EnumProperty:
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

    @classmethod
    def register_log_settings_class(cls, log: Logger):
        if cls.BHQRPRT_log_settings:
            bpy.utils.unregister_class(cls.BHQRPRT_log_settings)

        name = _eval_name(log.name)

        cls.BHQRPRT_log_settings = type(
            f"BHQRPRT_{name}_log_settings",
            (PropertyGroup,),
            {
                "__annotations__": {
                    "log_level": cls._get_prop_log_level(log, identifier="log_level"),
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


def _get_logger_stream_handler(log: Logger) -> None | logging.StreamHandler:
    for handler in log.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            return handler


def _get_logger_file_handler(log: Logger) -> None | logging.FileHandler:
    for handler in log.root.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler


def _get_bpy_struct_property_value(*, item: bpy_struct, identifier: str):
    return getattr(item, identifier, "(readonly)")


def _format_bpy_struct_property_value(*, value: bool | int | float | str | bpy_prop_array) -> str:
    if isinstance(value, float):
        return '%.6f' % value
    elif isinstance(value, str):
        if '\n' in value:
            return value.split('\n')[0][:-1] + " ... (multi-lined string skipped)"
        elif len(value) > 50:
            return value[:51] + " ... (long string skipped)"
    elif isinstance(value, bpy_prop_array):
        return ", ".join((_format_bpy_struct_property_value(value=_) for _ in value))

    return str(value)


def log_bpy_struct_properties(log: Logger, *, struct: bpy_struct, indent: int = 0) -> None:
    """Log properties of `bpy_struct`_. For pointer properties, recursive calls would be used.
    Long strings would be trimmed and for multi-line strings only first line would be logged. Floating point values would
    be formatted with 6 digits precision.

    :param log: Logger.
    :type log: Logger
    :param struct: Source structure to log properties from.
    :type struct: `bpy_struct`_
    :param indent: Indentation level, defaults to 0
    :type indent: int, optional
    """

    for prop in struct.bl_rna.properties:
        if prop.identifier in {
            # Blacklist of internal Blender properties, they should not be logged.
            'rna_type',
            'name',
            'bl_idname',
        }:
            continue

        if type(prop.rna_type) == bpy.types.PointerProperty:
            # Recursive call for pointer properties:
            log.debug(f"{prop.identifier} (\"{prop.name}\"):")
            log_bpy_struct_properties(log, struct=getattr(struct, prop.identifier), indent=indent + 1)
        else:
            value = _format_bpy_struct_property_value(
                value=_get_bpy_struct_property_value(item=struct, identifier=prop.identifier))
            log.debug(f"{' ' * 4 * indent}{prop.identifier}: {value}")


def register_reports(log: Logger, pref_cls: Type[AddonPreferences], directory: str):
    """Wrapper decorator to be used with extension's `register` function. It would setup logging system, add properties
    and draw method to existing user preferences class and set current logging level to log level saved in preferences.

    .. seealso::
        :func:`bhqrprt.setup_logger`
        :func:`bhqrprt.unregister_reports`

    .. note::

        This functionality available only from within Blender.

    :param log: Extension's logger.
    :type log: Logger
    :param pref_cls: Extension's user preferences class.
    :type pref_cls: Type[AddonPreferences]
    :param directory: Log files directory.
    :type directory: str
    """

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
                    panel.prop(self.bhqrprt, "log_level")
                    panel.prop(self.bhqrprt, "max_num_logs")

                    if handler := _get_logger_file_handler(log):
                        filepath = handler.baseFilename

                        directory, filename = os.path.split(filepath)

                        panel.operator(
                            operator="wm.path_open",
                            text="Open Log Files Directory",
                        ).filepath = directory

                        panel.operator(
                            operator="wm.path_open",
                            text=pgettext("Open Log: \"{filename}\"").format(filename=filename),
                        ).filepath = filepath

        return _draw_wrapper

    def _register_helper(register):
        def _register():
            _reports.setup_logger(log=log, directory=directory)

            _LogSettingsRegistry.register_log_settings_class(log)
            pref_cls.__annotations__['bhqrprt'] = PointerProperty(
                type=_LogSettingsRegistry.BHQRPRT_log_settings,
                name="Log Settings",
            )

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

                        _log_bpy_struct_properties(log, struct=addon_pref)

                    _SubmitIssueRegistry.ensure_register_submit_issue_operator(log)

        return _register

    return _register_helper


def unregister_reports(log: Logger):
    """Wrapper decorator to be used with extension's `unregister` function. It unregisters classes registered during
    :func:`register_reports` call and tears down reports.

    .. seealso::
        :func:`bhqrprt.register_reports`
        :func:`bhqrprt.teardown_logger`

    .. note::

        This functionality available only from within Blender.

    :param log: Extension's logger.
    :type log: Logger
    """

    def _unregister_helper(unregister):
        def _unregister():
            unregister()
            _LogSettingsRegistry.unregister_log_settings_class()
            _SubmitIssueRegistry.unregister_submit_issue_operator()
            _reports.teardown_logger(log=log)

        return _unregister

    return _unregister_helper


class _SubmitIssueRegistry:
    BHQRPRT_OT_submit_issue: None | Type[Operator] = None
    icon_value: int = 0

    @classmethod
    def ensure_register_submit_issue_operator(cls, log: Logger):
        if cls.BHQRPRT_OT_submit_issue:
            return

        name = _eval_name(log.name)

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
    """Template for display "Submit Issue" button in the UI. Underlying operator would open log files directory in 
    file browser and given `url` in web browser. 

    .. seealso::

        Function would work only if :func:`bhqrprt.register_reports` was used. Otherwise, it would do nothing.


    .. note::

        This functionality available only from within Blender.

    :param layout: Current UI layout.
    :type layout: `UILayout`_
    :param url: URL to be opened. Typically it should be GitHub issue tracker of extension's repository.
    :type url: str
    """

    if _SubmitIssueRegistry.BHQRPRT_OT_submit_issue:

        col = layout.column(align=False)
        col.alert = True
        col.scale_y = 1.5

        props = col.operator(
            operator=_SubmitIssueRegistry.BHQRPRT_OT_submit_issue.bl_idname,
            icon_value=_SubmitIssueRegistry.icon_value
        )
        props.url = url


def report_and_log(
    log: Logger,
    operator: Operator,
    *,
    level: int,
    message: str,
    **msg_kwargs: dict[str, Any]
) -> None:
    """Allows to make a report message and log simultaneously. For internationalization, the message will be
    translated and reported using the operator's translation context.

    .. note::

        This functionality available only from within Blender.

    :param log: Logger of the current module.
    :type log: Logger
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
    For security reasons, `filepath`, `directory` and `filename` keywords would be hidden. Only information about their
    existance would be logged.

    .. note::

        This functionality available only from within Blender.

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


def update_log_setting_changed(log: Logger, identifier: str) -> Callable[[bpy_struct, Context], None]:
    """Method for updating properties. If the property has been updated, it must be logged. Commonly used for
    logging preferences and scene changes.
    Long strings would be trimmed and for multi-line strings only first line would be logged. Floating point values would
    be formatted with 6 digits precision.

    :param log: Current module logger.
    :type log: Logger
    :param identifier: String identifier of the property in the class.
    :type identifier: str
    :return: Callable method to be used property update method.
    :rtype: Callable[[bpy_struct, Context], None]
    """

    def _log_setting_changed(self, _context: Context):
        value = _get_bpy_struct_property_value(item=self, identifier=identifier)
        value_fmt = _format_bpy_struct_property_value(value=value)
        log.debug(f"Setting updated \'{self.bl_rna.name}.{identifier}\': {value_fmt}")

    return _log_setting_changed
