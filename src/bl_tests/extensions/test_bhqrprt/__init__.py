# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import logging

import bpy

import bhqrprt4 as bhqrprt


log = logging.getLogger(__name__)


class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    test_prop: bpy.props.BoolProperty(
        update=bhqrprt.update_log_setting_changed(log, "test_prop")
    )

    def draw(self, context):
        bhqrprt.template_submit_issue(self.layout, url="https://github.com/ivan-perevala/lib_bhqrprt/issues")


class OBJECT_OT_bhqrprt_test(bpy.types.Operator):
    bl_idname = "object.bhqrprt_test"
    bl_label = "Test bhqrprt"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        return {'FINISHED'}

    def execute(self, context):
        return {'FINISHED'}


__classes = (
    Preferences,
    OBJECT_OT_bhqrprt_test,
)

_cls_register, _cls_unregister = bpy.utils.register_classes_factory(__classes)


@bhqrprt.register_reports(log, pref_cls=Preferences, directory=os.path.join(os.path.dirname(__file__), "logs"))
def register():
    _cls_register()


@bhqrprt.unregister_reports(log)
def unregister():
    _cls_unregister()
