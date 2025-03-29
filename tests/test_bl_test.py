import py_launch_blender as plb


def test_bl_test():
    with plb.BlenderIsolatedUserEnvironment() as env:
        env.pip_install_package("pytest")

        proc = plb.launch_blender(
            factory_startup=True,
            background=True,
            python_exit_code=255,
            python_expr=r"import pytest; pytest.main(['-v', '-s', 'src/bl_tests'])",
        )

        while proc.poll() is None:
            pass

        assert proc.returncode == 0
