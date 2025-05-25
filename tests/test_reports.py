# SPDX-FileCopyrightText: 2025 Ivan Perevala <ivan95perevala@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil
import subprocess
import pytest


@pytest.fixture
def blender_environ(tmpdir):
    original_src_dir = os.path.abspath("./src")
    original_ext_dir = os.path.join(original_src_dir, "bl_tests", "extensions")

    tmp_src_dir = os.path.join(tmpdir, "src")
    tmp_ext_dir = os.path.join(tmpdir, "extensions")

    shutil.copytree(original_src_dir, tmp_src_dir, dirs_exist_ok=True)
    shutil.copytree(original_ext_dir, tmp_ext_dir, dirs_exist_ok=True)

    env = os.environ.copy()
    env['PYTHONPATH'] = tmp_src_dir
    env['BLENDER_USER_EXTENSIONS'] = tmp_ext_dir
    return env


def test_one(blender_environ):
    blender = shutil.which('blender', path=os.environ.get("BLENDER_DIR"))

    cli = [
        blender,
        "--background",
        "--offline-mode",
        "--factory-startup",
        "--python-use-system-env",
        "--python-expr",
        "import bpy; bpy.ops.preferences.addon_enable(module='bl_ext.user_default.bhqrprt_test'); bpy.ops.bhqrprt.test()",
        "--python-exit-code", "255",
    ]
    proc = subprocess.Popen(cli, env=blender_environ, universal_newlines=True)

    while proc.poll() is None:
        pass

    assert proc.returncode == 0

    logs_dir = os.path.join(blender_environ['BLENDER_USER_EXTENSIONS'], "user_default", "bhqrprt_test", "logs")
    filename = None
    for _ in os.listdir(logs_dir):
        filename = _
        break

    assert filename, "Missing log file after running test addon"

    with open(os.path.join(logs_dir, filename), 'r') as file:
        data = file.read()

        assert data, "Log file is empty"
    
        # TODO: Actual log check here. Need a good way to test it, w.r.t. time and actual test addon
