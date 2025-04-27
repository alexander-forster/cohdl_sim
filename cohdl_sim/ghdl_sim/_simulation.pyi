from cohdl import Entity

from .._base_simulation import _BaseSimulator

class Simulator(_BaseSimulator):
    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        sim_dir: str = "sim",
        vhdl_dir: str = "sim",
        extra_vhdl_files: list[str] = None,
        extra_vhdl_files_post: list[str] = None,
        cast_vectors=None,
        simulator: str = "ghdl",
        sim_args: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
    ):
        """
        This is an alternative simulator that directly invokes GHDL without cocotb.

        The main advantage over the default simulator is that GHDL is loaded as a
        library into the current process. That makes it possible to use the Python
        debugger to set breakpoint and step threw testbench code. You can also define tests in
        Jupyter notebooks.

        ghdl_sim.Simulator is only available on Linux systems. ghdl must be installed
        before the cohdl_sim package because the FFI library is build during installation.
        In addition the ghdl-gcc backend in required.

        Differences to the default simulator:

        * `sim_dir` must be equal to `vhdl_dir`
        * `extra_env` is set in the local process environment
        """
