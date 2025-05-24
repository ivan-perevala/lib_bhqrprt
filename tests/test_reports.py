import os
import shutil
import subprocess


def test_one():
    blender = shutil.which('blender', path=os.environ.get("BLENDER_DIR"))

    cli = [
        blender,
        "--background",
        "--python-expr",
        "import bpy; bpy.ops.object.bhqrprt_test('EXEC_DEFAULT)",
        "--python-exit-code",
        "255",
    ]
    proc = subprocess.Popen(cli, env=os.environ, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    while proc.poll() is None:
        pass

    assert proc.returncode == 0
