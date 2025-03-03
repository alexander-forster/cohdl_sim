from __future__ import annotations

from cohdl import Entity, Port, BitVector, Unsigned, Signed, Null
from cohdl import std

from pathlib import Path
from functools import partial
from ._build_simulation import prepare_ghdl_simulation
from ._proxy_port import ProxyPort

import os

from cohdl_sim_ghdl_interface import GhdlInterface


class _Suspend:
    def __await__(self):
        yield None


_suspend = _Suspend()

global_alive_list = []


# ugly workaround to keep python objects referenced in the simulator alive
def _keep_alive(i):
    global_alive_list.append(i)
    return i


class Task:
    def __init__(self, simulator: Simulator):
        self._sim = simulator
        self._done = False
        self._continuation = None

    async def join(self):
        self._continuation = self._sim._current_coro
        while not self._done:
            await _suspend


class Simulator:
    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        simulator: str = "ghdl",
        sim_args: list[str] = None,
        sim_dir: str = "sim",
        vhdl_dir: str = "sim",
        mkdir=True,
        cast_vectors=None,
        extra_env: dict[str, str] | None = None,
        **kwargs,
    ):
        assert (
            simulator == "ghdl"
        ), "cohdl_sim.ghdl_sim only supports the ghdl simulator"

        assert (
            sim_dir == vhdl_dir,
            "cohdl_sim.ghdl_sim requires `sim_dir` and `vhdl_dir` to be the same",
        )

        # ghdl_sim executes in the current context
        # set extra-env locally
        if extra_env is not None:
            for name, val in extra_env.items():
                os.environ[name] = val

        if len(kwargs) != 0:
            print(f"ignoring additional arguments: {[*kwargs.keys()]}")

        build_dir = Path(build_dir)
        sim_dir = build_dir / sim_dir
        vhdl_dir = build_dir / vhdl_dir

        for dir in (build_dir, sim_dir, vhdl_dir):
            if not os.path.exists(dir):
                if mkdir:
                    os.makedirs(dir, exist_ok=True)
                else:
                    raise AssertionError(f"target directory '{dir}' does not exist")

        lib = std.VhdlCompiler.to_vhdl_library(entity)

        top_name = lib.top_entity().name()

        vhdl_sources = lib.write_dir(vhdl_dir)

        self._entity = entity
        self._simlib = prepare_ghdl_simulation(
            vhdl_sources, top_name, sim_dir, copy_files=False
        )

        self._top_name = top_name
        self._sim = GhdlInterface()
        self._sim_args = sim_args if sim_args is not None else []

        self._tb = None
        self._current_coro = None
        self._port_bv = cast_vectors

    def port_names(self) -> list[str]:
        return [name for name in self._entity._cohdl_info.ports]

    def _initial_fn(self):
        self._input_ports = {}
        self._output_ports = {}
        self._inout_ports = {}

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

            proxy = ProxyPort(
                port, self._sim.handle_by_name(f"{self._top_name}.{name}"), sim=self
            )

            setattr(EntityProxy, name, proxy)

            match port.direction():
                case Port.Direction.INPUT:
                    self._input_ports[name] = proxy
                case Port.Direction.OUTPUT:
                    self._output_ports[name] = proxy
                case Port.Direction.INOUT:
                    self._inout_ports[name] = proxy

        self._continue(self._tb(EntityProxy()))

    def _startup_function(self):
        # self._initial_fn()
        # global_alive_list.append(self._sim.add_startup_function(self._initial_fn))
        global_alive_list.append(self._sim.add_callback_delay(self._initial_fn, 0))

    def _continue(self, coro, name=None):
        prev_coro = self._current_coro
        self._current_coro = coro

        try:
            coro.send(None)
        except StopIteration:
            pass

        self._current_coro = prev_coro

    def test(self, testbench, sim_args=None):
        async def tb_wrapper(entity):
            await testbench(entity)
            self._sim.finish_simulation()

        sim_args = sim_args if sim_args is not None else self._sim_args

        self._tb = tb_wrapper
        self._sim.cleanup()

        global_alive_list.append(self._sim.add_startup_function(self._startup_function))
        self._sim.start(str(self._simlib), sim_args)
        self._sim.stop()

    async def _wait_picoseconds(self, picos: int):
        with _keep_alive(
            self._sim.add_callback_delay(
                partial(self._continue, self._current_coro, name="picos"), picos
            )
        ):
            await _suspend

    async def wait(self, duration: std.Duration):
        await self._wait_picoseconds(int(duration.picoseconds()))

    async def delta_step(self):
        with _keep_alive(
            self._sim.add_callback_delay(partial(self._continue, self._current_coro), 1)
        ):
            await _suspend

    async def rising_edge(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle,
            partial(self._continue, self._current_coro, name="rising_edge"),
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if (not prev_state) and new_state:
                    return
                prev_state = new_state

    async def falling_edge(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle,
            partial(self._continue, self._current_coro, name="falling_edge"),
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if prev_state and not new_state:
                    return
                prev_state = new_state

    async def any_edge(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle,
            partial(self._continue, self._current_coro, name="any_edge"),
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if prev_state != new_state:
                    return
                prev_state = new_state

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

    async def clock_cycles(self, signal: ProxyPort, num_cycles: int, rising=True):
        with self._sim.add_callback_value_change(
            signal._root._handle, partial(self._continue, self._current_coro)
        ):
            prev_state = signal.copy()

            if rising:
                while True:
                    await _suspend
                    new_state = signal.copy()

                    if (not prev_state) and new_state:
                        num_cycles -= 1
                        if num_cycles == 0:
                            return

                    prev_state = new_state
            else:
                while True:
                    await _suspend
                    new_state = signal.copy()

                    if prev_state and not new_state:
                        num_cycles -= 1
                        if num_cycles == 0:
                            return

                    prev_state = new_state

    async def value_change(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle, partial(self._continue, self._current_coro)
        ):
            await _suspend
            return

    async def value_true(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle, partial(self._continue, self._current_coro)
        ):
            while not signal:
                await _suspend

    async def value_false(self, signal: ProxyPort):
        with self._sim.add_callback_value_change(
            signal._root._handle, partial(self._continue, self._current_coro)
        ):
            while signal:
                await _suspend

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
        task = self.start_soon(coro)
        await self.delta_step()
        return task

    def start_soon(self, coro):

        task = Task(self)

        async def inner():
            await coro
            task._done = True

            if task._continuation is not None:
                self._continue(task._continuation)

        async def wrapper():
            await self.delta_step()
            self._continue(inner())

        self._continue(wrapper())

        return task

    def gen_clock(
        self,
        clk: ProxyPort,
        period_or_frequency: std.Duration = None,
        /,
        start_state=False,
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
                await self._wait_picoseconds(half)
                clk <<= not start_state
                await self._wait_picoseconds(half)

        self.start_soon(thread())

    def init_inputs(self, init_val=Null, /):
        for port in self._input_ports.values():
            port <<= init_val

    def init_outputs(self, init_val=Null, /):
        for port in self._output_ports.values():
            port <<= init_val

    def init_inouts(self, init_val=Null, /):
        for port in self._inout_ports.values():
            port <<= init_val
