"""
Alternative simulator backend, implemented using direct GHDL access.
Only available on Linux platforms.

By default cohdl_sim uses cocotb to simulate designs.

The direct GHDL simulator supports fewer features.
It cannot be combined with cocotb libraries.
The main advantage is, that the entire simulation is performed
in a single Python context. Debuggers can be used to step threw
testbench code without additional setup.
Unlike the cocotb backend the direct GHDL access is usable from
jupyter notebooks.
"""

import os
import subprocess

assert os.name == "posix", "the ghdl_sim simulator is only supported in Linux"

success, output = subprocess.getstatusoutput("ghdl-gcc --version")
assert success == 0, "ghdl_sim requires `ghdl` and the ghdl backend `ghdl-gcc`"

try:
    import cohdl_sim_ghdl_interface
except:
    raise AssertionError(
        "The internal module cohdl_sim_ghdl_interface is not installed.\n"
        "A possible reason for this error is, that the ghdl command was not available while `pip install cohdl_sim` was executed.\n"
        "Try to install ghdl and ghdl-gcc and then reinstall cohdl_sim.\n"
    )


from ._simulation import Simulator
