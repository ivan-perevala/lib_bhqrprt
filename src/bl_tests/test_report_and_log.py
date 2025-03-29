# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# This test intended to run from within Blender.
# See file://./../../tests/test_bl_test.py" which launches Blender in isolated environment.

import logging
import tempfile

import bpy

import bhqrprt

log = logging.getLogger()

tmpdir: tempfile.TemporaryDirectory

##########################
# Objects Used For Testing
##########################


# Here dynamic creation of operator classes is used to reduce the amount of code in the example.
# In general, we are interested in the `execute` method, which is wrapped in a decorator.
def _report_operator_by_logging_level_helper(*, level_name: str, level: int):

    def execute(self, context: bpy.types.Context):
        # This call will make a report in the user interface, write the message to a file,
        # and display it in the console.
        bhqrprt.report_and_log(
            log, self,
            level=level,
            message=f"{level_name} Report Test",
        )
        return {'FINISHED'}

    return execute


_REPORT_OPERATORS_BY_LOGGING_LEVEL = tuple(
    type(
        f"BHQRPRT_OT_test_report_{level_name.lower()}",
        (bpy.types.Operator,),
        dict(
            bl_idname=f"bhqrprt.test_report_{level_name.lower()}",
            bl_label=level_name.capitalize(),
            bl_options={'REGISTER'},
            execute=_report_operator_by_logging_level_helper(level_name=level_name, level=level)
        )
    )
    for level_name, level in logging.getLevelNamesMapping().items()
)


class BHQRPRT_OT_test_execution(bpy.types.Operator):
    bl_idname = "bhqrprt.test_execution"
    bl_label = "Execute"
    bl_options = {'REGISTER'}

    # Here the operator's execution method uses a package decorator, so first, a log is made
    # about the start of the execution, then the original method is called (it may contain initial messages),
    # and after that, a log is output about the status and execution time.
    @bhqrprt.log_execution_helper
    def execute(self, context):
        log.info("Logging info during operator execution call")
        return {'FINISHED'}


_classes = (
    BHQRPRT_OT_test_execution,
    *_REPORT_OPERATORS_BY_LOGGING_LEVEL,
)


_cls_register, _cls_unregister = bpy.utils.register_classes_factory(_classes)


def register():
    _cls_register()


def unregister():
    _cls_unregister()


#######
# Tests
#######


def setup_module():
    global tmpdir
    tmpdir = tempfile.TemporaryDirectory()

    bhqrprt.setup_logger(directory=tmpdir.name)

    register()


def teardown_module():
    global tmpdir

    unregister()

    bhqrprt.teardown_logger()

    tmpdir.cleanup()


def test_logging_level_debug(caplog, capsys):
    """Test report and log at debug logging level.

    Expected results:

    * Full log message written to log file.
    * Info message from Blender report function.
    * No output from logger into console.
    """

    with caplog.at_level(logging.DEBUG):
        bpy.ops.bhqrprt.test_report_debug('EXEC_DEFAULT')  # type: ignore

        rec = caplog.records[-1]

        assert rec.levelno == logging.DEBUG
        assert rec.message == "DEBUG Report Test"

        captured = capsys.readouterr()

        assert captured.out == "Info: DEBUG Report Test\n"

        fp = bhqrprt.get_log_filepath()
        assert fp
        with open(fp, 'r') as file:
            data = file.readlines()

            assert data[-1].endswith(" root report_and_log: DEBUG Report Test\n")
