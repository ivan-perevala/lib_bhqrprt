# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# type: ignore

from __future__ import annotations

import os
import logging

import bpy

import bhqrprt4 as bhqrprt

assert __package__

log = logging.getLogger(__name__)


def get_preferences():
    addon_pref = bpy.context.preferences.addons[__package__].preferences
    return addon_pref


class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    test_prop: bpy.props.BoolProperty(
        update=bhqrprt.update_log_setting_changed(log, "test_prop")
    )

    def draw(self, context):
        bhqrprt.template_submit_issue(self.layout, url="https://github.com/ivan-perevala/lib_bhqrprt/issues")


class BHQRPRT_OT_test(bpy.types.Operator):
    bl_idname = "bhqrprt.test"
    bl_label = "Test bhqrprt"
    bl_options = {'INTERNAL'}

    bool_prop: bpy.props.BoolProperty(default=False, name="Test Bool")
    float_prop: bpy.props.FloatProperty(default=1e-5, name="Test Float")
    int_prop: bpy.props.IntProperty(default=100, name="Test Int")
    str_prop: bpy.props.StringProperty(default="Some String", name="Test Str")

    @bhqrprt.operator_report(log)
    def invoke(self, context, event):
        return {'FINISHED'}

    @bhqrprt.operator_report(log)
    def execute(self, context):
        bhqrprt.report_and_log(log, self, level=logging.DEBUG, message="Test debug message")
        bhqrprt.report_and_log(log, self, level=logging.INFO, message="Test info message")
        bhqrprt.report_and_log(log, self, level=logging.WARNING, message="Test warning message")
        # bhqrprt.report_and_log(log, self, level=logging.ERROR, message="Test error message")
        bpy.ops.wm.read_homefile()
        return {'FINISHED'}


__classes = (
    Preferences,
    BHQRPRT_OT_test,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(__classes)


@bpy.app.handlers.persistent
def handler_load_post(_=None):
    addon_pref = get_preferences()
    bhqrprt.log_bpy_struct_properties(log, struct=addon_pref)


@bhqrprt.register_reports(log, pref_cls=Preferences, directory=os.path.join(os.path.dirname(__file__), "logs"))
def register():
    _cls_register()
    bpy.app.handlers.load_post.append(handler_load_post)


@bhqrprt.unregister_reports(log)
def unregister():
    bpy.app.handlers.load_post.remove(handler_load_post)
    _cls_unregister()
