from cohdl import Entity, Signal

from ._base_simulation import _BaseSimulator

class Simulator(_BaseSimulator):
    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        sim_dir: str = "sim",
        vhdl_dir: str = "vhdl",
        extra_vhdl_files: list[str] = None,
        extra_vhdl_files_post: list[str] = None,
        cast_vectors=None,
        simulator: str = "ghdl",
        sim_args: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
        cocotb_extra_args: dict[str, str] | None = None,
    ):
        """
        Simulator takes a CoHDL entity, generates VHDL code from it
        and starts a cocotb test session.

        * `entity` tested entity type
        * `build_dir` simulation outputs are written to this directory
        * `sim_dir` name of directory inside build_dir that is used for simulator output
        * `vhdl_dir` name of directory inside build_dir where generated VHDL files are written
        * `extra_vhdl_files` list of paths to additional VHDL files
        * `extra_vhdl_files_post` like `extra_vhdl_files` but arguments are analyzed after CoHDL entities
        * `cast_vectors` when set to cohdl.Signed or cohdl.Unsigned all BitVector ports are converted
                            to the corresponding type

        The following arguments are forwarded to cocotb:

        * `simulator`
        * `sim_args`
        * `extra_env`
        * `cocotb_extra_args` (as additional keyword arguments)
        """

    def get_dut(self):
        """
        return the cocotb design under test object
        """

    def freeze(self, port: Signal, /):
        """
        freeze the signal in its current state
        """

    def release(self, port: Signal, /):
        """
        release a frozen signal
        """
