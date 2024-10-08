from cohdl import Entity, Signal, Bit
from cohdl import std

class Simulator:
    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        simulator: str = "ghdl",
        sim_args: list[str] | None = None,
        sim_dir: str = "sim",
        vhdl_dir: str = "vhdl",
        mkdir: bool = True,
        cast_vectors=None,
        extra_env: dict[str, str] | None = None,
        extra_vhdl_files: list[str] = None,
        use_build_cache: bool = False,
        **kwargs,
    ):
        """
        Simulator takes a CoHDL entity, generates VHDL code from it
        and starts a cocotb test session.

        build_dir, sim_dir, vhdl_dir and mkdir are used to customize the
        location of build and simulation output. `extra_vhdl_files`
        is a list of additional vhdl sources to include in the build.

        When `use_build_cache` is set to True, the design is only build
        once. Subsequent tests will use the vhdl-sources of that build.
        This can be useful to speedup test runs, the user must take care
        to set this value to False whenever a new build is needed.

        The other arguments are forwarded to cocotb_test.simulator.run().
        """

    async def wait(self, duration: std.Duration):
        """
        wait for a given simulation duration
        """

    async def delta_step(self):
        """
        run simulation for a short time to update output ports
        """

    async def rising_edge(self, signal: Signal[Bit]):
        """
        wait for rising edge on signal
        """

    async def falling_edge(self, signal: Signal[Bit]):
        """
        wait for falling edge on signal
        """

    async def any_edge(self, signal: Signal[Bit]):
        """
        wait for changes of signal
        """

    async def clock_cycles(self, signal: Signal[Bit], num_cycles: int, rising=True):
        """
        wait for a number of clock cycles,
        rising determines whether rising or falling edges are counted
        """

    async def value_change(self, signal: Signal):
        """
        wait until signal changes
        """

    async def value_true(self, signal: Signal):
        """
        wait until signal becomes truthy
        """

    async def value_false(self, signal: Signal):
        """
        wait until signal becomes falsy
        """

    async def true_on_rising(
        self, clk: Signal[Bit], cond, *, timeout: int | None = None
    ):
        """
        Wait until cond is true after a rising edge of the clock signal.
        `cond` can be a port or a callable taking no arguments returning a boolean value.
        Raises an exception if the condition remains false for more than timeout rising edges.
        """

    async def true_on_falling(
        self, clk: Signal[Bit], cond, *, timeout: int | None = None
    ):
        """
        Wait until cond is true after a falling edge of the clock signal.
        `cond` can be a port or a callable taking no arguments returning a boolean value.
        Raises an exception if the condition remains false for more than timeout falling edges.
        """

    async def start(self, coro):
        """
        Run coro in parallel task.
        `coro` will start immediately (current task is suspended).
        """

    def start_soon(self, coro):
        """
        Run coro in parallel task.
        `coro` will start once the current task is suspended.
        """

    def gen_clock(
        self,
        clk: Signal[Bit],
        period_or_frequency: std.Duration | std.Frequency,
        /,
        start_state=False,
    ) -> None:
        """
        Start a parallel task that produces a clock signal
        with the specified period or frequency on `clk`.
        """

    def get_dut(self):
        """
        return the cocotb design under test object
        """

    def test(self, testbench):
        """
        decorator turns coroutines into test benches
        """
        return testbench

    def freeze(self, port: Signal):
        """
        freeze the signal in its current state
        """

    def release(self, port: Signal):
        """
        release a frozen signal
        """
