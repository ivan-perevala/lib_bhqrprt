import os
import shutil


def test_one():
    blender = shutil.which('blender', path=os.environ.get("BLENDER_DIR"))

    assert blender
