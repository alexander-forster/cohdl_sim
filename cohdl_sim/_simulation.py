import os
import cocotb

from cocotb.triggers import (
    Timer,
    Edge,
)

from cocotb_test import simulator as cocotb_simulator

from cohdl import Entity, Port, BitVector, Signed, Unsigned
from cohdl import std

from ._proxy_port import ProxyPort


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
        **kwargs,
    ):
        sim_args = [] if sim_args is None else sim_args
        extra_env = {} if extra_env is None else extra_env

        # This code is evaluated twice. Once in normal user code
        # to setup the test environment and again from another process
        # started by cocotb_simulator.run().
        # Use an environment variable to determine current mode.
        if os.getenv("COHDLSIM_TEST_RUNNING") is None:
            # running in normal user code
            # run CoHDL design into VHDL code and
            # start cocotb simulator

            sim_dir = f"{build_dir}/{sim_dir}"
            vhdl_dir = f"{build_dir}/{vhdl_dir}"

            if not os.path.exists(vhdl_dir):
                if mkdir:
                    os.makedirs(vhdl_dir, exist_ok=True)
                else:
                    raise AssertionError(
                        f"target directory '{vhdl_dir}' does not exist"
                    )

            lib = std.VhdlCompiler.to_vhdl_library(entity)

            top_name = lib.top_entity().name()
            entity_names = [sub.name() for sub in lib._entities]

            lib.write_dir(vhdl_dir)

            vhdl_sources = [f"{vhdl_dir}/{name}.vhd" for name in entity_names]

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

    async def wait(self, duration: std.Duration):
        await Timer(int(duration.picoseconds()), units="ps")

    async def delta_step(self):
        await Timer(1, units="step")

    async def rising_edge(self, signal: ProxyPort):
        await signal._rising_edge()
        await self.delta_step()

    async def falling_edge(self, signal: ProxyPort):
        await signal._falling_edge()
        await self.delta_step()

    async def any_edge(self, signal: ProxyPort):
        await signal._edge()
        await self.delta_step()

    async def clock_cycles(self, signal: ProxyPort, num_cycles: int, rising=True):
        await signal._clock_cycles(num_cycles, rising)
        await self.delta_step()

    async def value_change(self, signal: ProxyPort):
        await Edge(signal._cocotb_port)

    async def value_true(self, signal: ProxyPort):
        while not signal:
            await signal._edge()

    async def value_false(self, signal: ProxyPort):
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

    async def start(self, coro):
        await cocotb.start(coro)

    def start_soon(self, coro):
        cocotb.start_soon(coro)

    def gen_clock(
        self, clk, period_or_frequency: std.Duration = None, /, start_state=False
    ):
        if isinstance(period_or_frequency, (std.Frequency, std.Duration)):
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

    def test(self, testbench):
        @cocotb.test()
        async def helper(dut):
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

                setattr(EntityProxy, name, ProxyPort(port, getattr(dut, name)))

            # first delta step to load default values
            await Timer(1, units="step")
            # await self.delta_step()

            # use proxy entity instead of cocotb dut
            # in testbench function
            await testbench(EntityProxy())

        return helper

    def freeze(self, port: ProxyPort):
        port.freeze()

    def release(self, port: ProxyPort):
        port.release()
