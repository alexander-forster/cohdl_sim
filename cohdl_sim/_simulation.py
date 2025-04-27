import os
import cocotb
import functools

from cocotb.triggers import (
    Timer,
    Edge,
)

from cocotb_test import simulator as cocotb_simulator

from cohdl import Entity, Port, BitVector, Signed, Unsigned
from cohdl import std

from ._proxy_port import ProxyPort
from ._base_simulation import _GenericParams, _BaseSimulator


class Task:
    def __init__(self, handle):
        self._handle = handle

    async def join(self):
        await self._handle.join()


class Simulator(_BaseSimulator):

    def _init_impl(self, p: _GenericParams, cocotb_extra_args=None):
        from cohdl_sim._build_cache import write_cache_file, load_cache_file

        # This code is evaluated twice. Once in normal user code
        # to setup the test environment and again from another process
        # started by cocotb_simulator.run().
        # Use an environment variable to determine current mode.
        if os.getenv("COHDLSIM_TEST_RUNNING") is None:
            # running in normal user code
            # run CoHDL design into VHDL code and
            # start cocotb simulator

            top_name = p.entity._cohdl_info.name

            if not p.use_build_cache:
                lib = std.VhdlCompiler.to_vhdl_library(p.entity)
                vhdl_sources = (
                    p.extra_vhdl_files
                    + lib.write_dir(p.vhdl_dir)
                    + p.extra_vhdl_files_post
                )

                write_cache_file(p.cache_file, p.entity, vhdl_sources=vhdl_sources)
            else:
                cache_content = load_cache_file(p.cache_file, p.entity)
                vhdl_sources = cache_content.vhdl_sources

            # cocotb_simulator.run() requires the module name
            # of the Python file containing the test benches

            import inspect
            import pathlib

            filename = inspect.stack()[2].filename
            filename = pathlib.Path(filename).stem

            cocotb_extra_args = {} if cocotb_extra_args is None else cocotb_extra_args

            cocotb_simulator.run(
                simulator=p.simulator,
                sim_args=p.sim_args,
                sim_build=p.sim_dir,
                vhdl_sources=vhdl_sources,
                toplevel=top_name.lower(),
                module=filename,
                extra_env={"COHDLSIM_TEST_RUNNING": "True", **p.extra_env},
                **cocotb_extra_args,
            )
        else:
            # running in simulator process
            # initialize members used by Simulator.test

            # instantiate entity to generate dynamic ports
            p.entity(_cohdl_instantiate_only=True)
            self._dut = None

    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        simulator: str = "ghdl",
        sim_args: list[str] | None = None,
        sim_dir: str = "sim",
        vhdl_dir: str = "vhdl",
        cast_vectors=None,
        extra_env: dict[str, str] | None = None,
        extra_vhdl_files: list[str] = None,
        use_build_cache: bool = False,
        cocotb_extra_args: dict[str, str] | None = None,
    ):
        p = _GenericParams(
            entity=entity,
            build_dir=build_dir,
            simulator=simulator,
            sim_args=sim_args,
            sim_dir=sim_dir,
            vhdl_dir=vhdl_dir,
            cast_vectors=cast_vectors,
            extra_env=extra_env,
            extra_vhdl_files=extra_vhdl_files,
            use_build_cache=use_build_cache,
        )

        super().__init__(p)
        self._init_impl(p, cocotb_extra_args=cocotb_extra_args)

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

    #
    #

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
            entity = self._params.entity
            entity_name = entity.__name__

            class EntityProxy(entity):
                def __new__(cls):
                    return object.__new__(cls)

                def __init__(self):
                    pass

                def __str__(self):
                    return entity_name

                def __repr__(self):
                    return entity_name

            for name, port in entity._cohdl_info.ports.items():

                port_bv = self._params.cast_vectors

                if port_bv is not None:
                    port_type = type(Port.decay(port))

                    if issubclass(port_type, BitVector) and not (
                        issubclass(port_type, (Signed, Unsigned))
                    ):
                        if port_bv is Unsigned:
                            port = port.unsigned
                        elif port_bv is Signed:
                            port = port.signed
                        else:
                            raise AssertionError(
                                f"invalid default vector port type {port_bv}"
                            )

                proxy = ProxyPort(port, None, getattr(dut, name))
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
