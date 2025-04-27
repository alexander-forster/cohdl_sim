import unittest
import importlib

from examples import _config

# basic test to check that all example compile
# and run without error in both simulators


def repeat_with_ghdl_sim(module):
    _config._use_ghdl_direct = True

    try:
        importlib.reload(module)
    finally:
        _config._use_ghdl_direct = False


class Tester(unittest.TestCase):

    def test_01(self):
        from examples import example_01_simple

        repeat_with_ghdl_sim(example_01_simple)

    def test_02(self):
        from examples import example_02_vectors

        repeat_with_ghdl_sim(example_02_vectors)

    def test_03(self):
        from examples import example_03_sequential

        repeat_with_ghdl_sim(example_03_sequential)

    def test_04(self):
        from examples import example_04_await_change

        repeat_with_ghdl_sim(example_04_await_change)

    def test_05(self):
        from examples import example_05_casts

        repeat_with_ghdl_sim(example_05_casts)

    def test_06(self):
        from examples import example_06_dynamic_ports

        repeat_with_ghdl_sim(example_06_dynamic_ports)

    def test_07(self):
        from examples import example_07_join_tasks

        repeat_with_ghdl_sim(example_07_join_tasks)

    def test_08(self):
        from examples import example_08_axi

        repeat_with_ghdl_sim(example_08_axi)

    def test_09(self):
        from examples import example_09_nested_entities

        repeat_with_ghdl_sim(example_09_nested_entities)
