from cohdl import Signal, Bit
from cohdl import std
from cohdl import Null

from ._proxy_port import ProxyPort

class Task:
    async def join(self):
        """
        Wait until the task is done
        """

class _BaseSimulator:
    def test(self, testbench, /):
        """
        decorator that turns coroutines into test benches
        """
        return testbench

    async def wait(self, duration: std.Duration, /) -> None:
        """
        wait for a given simulation duration
        """

    async def delta_step(self) -> None:
        """
        run simulation for a short time to update output ports
        """

    async def rising_edge(self, signal: Signal[Bit], /) -> None:
        """
        wait for rising edge on signal
        """

    async def falling_edge(self, signal: Signal[Bit], /) -> None:
        """
        wait for falling edge on signal
        """

    async def any_edge(self, signal: Signal[Bit], /) -> None:
        """
        wait for changes of signal
        """

    async def clock_cycles(
        self, signal: Signal[Bit] | std.Clock, num_cycles: int, rising=True
    ):
        """
        wait for a number of clock cycles,
        `rising` determines whether rising or falling edges are counted
        """

    async def value_change(self, signal: Signal, /) -> None:
        """
        wait until signal changes
        """

    async def value_true(self, signal: Signal, /) -> None:
        """
        wait until signal becomes truthy
        """

    async def value_false(self, signal: Signal, /) -> None:
        """
        wait until signal becomes falsy
        """

    async def start(self, coro, /) -> Task:
        """
        Run coro in parallel task.
        `coro` will start immediately (current task is suspended).
        """

    def start_soon(self, coro, /) -> Task:
        """
        Run coro in parallel task.
        `coro` will start once the current task is suspended.
        """

    def gen_clock(
        self,
        clk: Signal[Bit] | std.Clock,
        period_or_frequency: std.Duration | std.Frequency | None = None,
        /,
        start_state=False,
    ) -> None:
        """
        Start a parallel task that produces a clock signal
        with the specified period or frequency on `clk`.

        The `period_of_frequency` parameter is mandatory unless
        `clk` is a `std.Clock` and defines its own frequency.
        """

    def init_inputs(self, init_val=Null, /):
        """
        assign `init_val` to all input ports of the tested entity
        """

    def init_outputs(self, init_val=Null, /):
        """
        assign `init_val` to all output ports of the tested entity
        """

    def init_inouts(self, init_val=Null, /):
        """
        assign `init_val` to all inout ports of the tested entity
        """

    async def clock_edge(self, clk: std.Clock, /):
        """
        wait for active edge on the clock
        """

    async def reset_cond(self, reset: std.Reset, /) -> None:
        """
        wait until the reset condition becomes true
        """

    async def true_on_rising(
        self, clk: Signal[Bit], cond, *, timeout: int | None = None
    ) -> None:
        """
        Wait until cond is true after a rising edge of the clock signal.
        `cond` can be a port or a callable taking no arguments returning a boolean value.
        Raises an exception if the condition remains false for more than timeout rising edges.
        """

    async def true_on_falling(
        self, clk: Signal[Bit], cond, *, timeout: int | None = None
    ) -> None:
        """
        Wait until cond is true after a falling edge of the clock signal.
        `cond` can be a port or a callable taking no arguments returning a boolean value.
        Raises an exception if the condition remains false for more than timeout falling edges.
        """

    async def true_on_clk(self, clk: std.Clock, cond, *, timeout: int | None = None):
        """
        Wait until cond is true after a clock tick.
        `cond` can be a port or a callable taking no arguments returning a boolean value.
        Raises an exception if the condition remains false for more than timeout ticks.
        """

    async def true_after_rising(
        self, clk: ProxyPort, cond, *, timeout: int | None = None
    ):
        while True:
            await self.rising_edge(clk)
            await self.delta_step()

            if cond():
                return

            if timeout is not None:
                assert timeout != 0, "timeout while waiting for condition"
                timeout -= 1

    async def true_after_falling(
        self, clk: ProxyPort, cond, *, timeout: int | None = None
    ):
        while True:
            await self.falling_edge(clk)
            await self.delta_step()

            if cond():
                return

            if timeout is not None:
                assert timeout != 0, "timeout while waiting for condition"
                timeout -= 1

    async def true_after_clk(self, clk: std.Clock, cond, *, timeout: int | None = None):
        if clk.is_rising_edge():
            await self.true_after_rising(clk.signal(), cond, timeout=timeout)
        else:
            await self.true_after_falling(clk.signal(), cond, timeout=timeout)
