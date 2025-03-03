import os
import cocotb
import functools

from pathlib import Path

from cocotb.triggers import (
    Timer,
    Edge,
)

from cocotb_test import simulator as cocotb_simulator

from cohdl import Entity, Port, BitVector, Signed, Unsigned
from cohdl import std
from cohdl import Null

from ._proxy_port import ProxyPort


class Task:
    def __init__(self, handle):
        self._handle = handle

    async def join(self):
        await self._handle.join()


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
        from cohdl_sim._build_cache import write_cache_file, load_cache_file

        build_dir = Path(build_dir)

        sim_args = [] if sim_args is None else sim_args
        extra_env = {} if extra_env is None else extra_env

        vhdl_sources = list(extra_vhdl_files) if extra_vhdl_files is not None else []

        # This code is evaluated twice. Once in normal user code
        # to setup the test environment and again from another process
        # started by cocotb_simulator.run().
        # Use an environment variable to determine current mode.
        if os.getenv("COHDLSIM_TEST_RUNNING") is None:
            # running in normal user code
            # run CoHDL design into VHDL code and
            # start cocotb simulator

            sim_dir = build_dir / sim_dir
            vhdl_dir = build_dir / vhdl_dir
            cache_file = build_dir / ".build-cache.json"

            # use cache file if it exists, rebuild it otherwise
            use_build_cache = use_build_cache and cache_file.exists()

            if not os.path.exists(vhdl_dir):
                if mkdir:
                    os.makedirs(vhdl_dir, exist_ok=True)
                else:
                    raise AssertionError(
                        f"target directory '{vhdl_dir}' does not exist"
                    )

            top_name = entity._cohdl_info.name

            if not use_build_cache:
                lib = std.VhdlCompiler.to_vhdl_library(entity)
                vhdl_sources += lib.write_dir(vhdl_dir)

                write_cache_file(cache_file, entity, vhdl_sources=vhdl_sources)
            else:
                cache_content = load_cache_file(cache_file, entity)
                vhdl_sources = cache_content.vhdl_sources

            # cocotb_simulator.run() requires the module name
            # of the Python file containing the test benches

            import inspect
            import pathlib

            filename = inspect.stack()[1].filename
            filename = pathlib.Path(filename).stem

            cocotb_simulator.run(
                simulator=simulator,
                sim_args=sim_args,
                sim_build=sim_dir,
                vhdl_sources=vhdl_sources,
                toplevel=top_name.lower(),
                module=filename,
                extra_env={"COHDLSIM_TEST_RUNNING": "True", **extra_env},
                **kwargs,
            )
        else:
            # instantiate entity to generate dynamic ports
            entity(_cohdl_instantiate_only=True)

            # running in simulator process
            # initialize members used by Simulator.test

            self._entity = entity
            self._dut = None
            self._port_bv = cast_vectors

    async def wait(self, duration: std.Duration, /):
        await Timer(int(duration.picoseconds()), units="ps")

    async def delta_step(self):
        await Timer(1, units="step")

    async def rising_edge(self, signal: ProxyPort, /):
        await signal._rising_edge()

    async def falling_edge(self, signal: ProxyPort, /):
        await signal._falling_edge()

    async def any_edge(self, signal: ProxyPort, /):
        await signal._edge()

    async def clock_edge(self, clk: std.Clock, /):
        Edge = std.Clock.Edge

        match clk.edge():
            case Edge.RISING:
                await self.rising_edge(clk.signal())
            case Edge.FALLING:
                await self.falling_edge(clk.signal())
            case Edge.BOTH:
                await self.any_edge(clk.signal())
            case _:
                raise AssertionError(f"invalid clock edge {clk.edge()}")

    async def reset_cond(self, reset: std.Reset, /):
        if reset.is_active_high():
            if reset.is_async():
                await self.value_true(reset.signal())
            else:
                await self.rising_edge(reset.signal())
        else:
            if reset.is_async():
                await self.value_false(reset.signal())
            else:
                await self.falling_edge(reset.signal())

    async def clock_cycles(self, signal: ProxyPort, num_cycles: int, rising=True):
        if isinstance(signal, std.Clock):
            signal = signal.signal()

        await signal._clock_cycles(num_cycles, rising)

    async def value_change(self, signal: ProxyPort, /):
        await Edge(signal._cocotb_port)

    async def value_true(self, signal: ProxyPort, /):
        while not signal:
            await signal._edge()

    async def value_false(self, signal: ProxyPort, /):
        while signal:
            await signal._edge()

    async def true_on_rising(self, clk: ProxyPort, cond, *, timeout: int | None = None):
        while True:
            await self.rising_edge(clk)

            if cond():
                return

            if timeout is not None:
                assert timeout != 0, "timeout while waiting for condition"
                timeout -= 1

    async def true_on_falling(
        self, clk: ProxyPort, cond, *, timeout: int | None = None
    ):
        while True:
            await self.falling_edge(clk)

            if cond():
                return

            if timeout is not None:
                assert timeout != 0, "timeout while waiting for condition"
                timeout -= 1

    async def true_on_clk(self, clk: std.Clock, cond, *, timeout: int | None = None):
        if clk.is_rising_edge():
            await self.true_on_rising(clk.signal(), cond, timeout=timeout)
        else:
            await self.true_on_falling(clk.signal(), cond, timeout=timeout)

    #
    #

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

    async def start(self, coro, /):
        return Task(await cocotb.start(coro))

    def start_soon(self, coro, /):
        return Task(cocotb.start_soon(coro))

    def gen_clock(
        self, clk, period_or_frequency: std.Duration = None, /, start_state=False
    ):
        if isinstance(clk, std.Clock):
            if period_or_frequency is None:
                period_or_frequency = clk.frequency()

            clk = clk.signal()

        assert isinstance(period_or_frequency, (std.Frequency, std.Duration))

        period = period_or_frequency.period()

        half = int(period.picoseconds()) // 2

        async def thread():
            nonlocal clk
            while True:
                clk <<= start_state
                await Timer(half, units="ps")
                clk <<= not start_state
                await Timer(half, units="ps")

        self.start_soon(thread())

    def get_dut(self):
        assert (
            self._dut is not None
        ), "get_dut may only be called from a testbench function running in cocotb"
        return self._dut

    def test(self, testbench, /):
        @cocotb.test()
        @functools.wraps(testbench)
        async def helper(dut):
            self._ports = {}
            self._input_ports = {}
            self._output_ports = {}
            self._inout_ports = {}

            self._dut = dut
            entity_name = self._entity.__name__

            class EntityProxy(self._entity):
                def __new__(cls):
                    return object.__new__(cls)

                def __init__(self):
                    pass

                def __str__(self):
                    return entity_name

                def __repr__(self):
                    return entity_name

            for name, port in self._entity._cohdl_info.ports.items():

                if self._port_bv is not None:
                    port_type = type(Port.decay(port))

                    if issubclass(port_type, BitVector) and not (
                        issubclass(port_type, (Signed, Unsigned))
                    ):
                        if self._port_bv is Unsigned:
                            port = port.unsigned
                        elif self._port_bv is Signed:
                            port = port.signed
                        else:
                            raise AssertionError(
                                f"invalid default vector port type {self._port_bv}"
                            )

                proxy = ProxyPort(port, getattr(dut, name))
                setattr(EntityProxy, name, proxy)

                self._ports[name] = proxy

                match port.direction():
                    case Port.Direction.INPUT:
                        self._input_ports[name] = proxy
                    case Port.Direction.OUTPUT:
                        self._output_ports[name] = proxy
                    case Port.Direction.INOUT:
                        self._inout_ports[name] = proxy

            # first delta step to load default values
            await Timer(1, units="step")
            # await self.delta_step()

            # use proxy entity instead of cocotb dut
            # in testbench function
            await testbench(EntityProxy())

        return helper

    def freeze(self, port: ProxyPort, /):
        port.freeze()

    def release(self, port: ProxyPort, /):
        port.release()

    def init_inputs(self, init_val=Null, /):
        for port in self._input_ports.values():
            port <<= init_val

    def init_outputs(self, init_val=Null, /):
        for port in self._output_ports.values():
            port <<= init_val

    def init_inouts(self, init_val=Null, /):
        for port in self._inout_ports.values():
            port <<= init_val
