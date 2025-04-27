from __future__ import annotations

from cohdl import Entity, Port, BitVector, Unsigned, Signed, Null
from cohdl import std

from pathlib import Path
from functools import partial
from ._build_simulation import prepare_ghdl_simulation
from ._proxy_port import ProxyPort
from .._base_simulation import _GenericParams, _BaseSimulator

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


class Simulator(_BaseSimulator):

    def _init_impl(self, p: _GenericParams):
        from cohdl_sim._build_cache import write_cache_file, load_cache_file

        assert (
            p.simulator == "ghdl"
        ), "cohdl_sim.ghdl_sim only supports the ghdl simulator"

        assert (
            p.sim_dir == p.vhdl_dir
        ), "cohdl_sim.ghdl_sim requires `sim_dir` and `vhdl_dir` to be the same"

        # ghdl_sim executes in the current context
        # set extra-env locally
        for name, val in p.extra_env.items():
            os.environ[name] = val

        top_name = p.entity._cohdl_info.name
        self._entity = p.entity
        self._top_name = top_name

        if not p.use_build_cache:
            lib = std.VhdlCompiler.to_vhdl_library(p.entity)
            vhdl_sources = (
                p.extra_vhdl_files + lib.write_dir(p.vhdl_dir) + p.extra_vhdl_files_post
            )
            write_cache_file(p.cache_file, p.entity, vhdl_sources=vhdl_sources)
        else:
            cache_content = load_cache_file(p.cache_file, p.entity)
            vhdl_sources = cache_content.vhdl_sources

        self._simlib = prepare_ghdl_simulation(
            vhdl_sources, top_name, p.sim_dir, copy_files=False
        )

        self._sim = GhdlInterface()
        self._sim_args = p.sim_args

        self._tb = None
        self._current_coro = None
        self._port_bv = p.cast_vectors

    def __init__(
        self,
        entity: type[Entity],
        *,
        build_dir: str = "build",
        simulator: str = "ghdl",
        sim_args: list[str] = None,
        sim_dir: str = "sim",
        vhdl_dir: str = "sim",
        cast_vectors=None,
        extra_env: dict[str, str] | None = None,
        extra_vhdl_files: list[str] = None,
        extra_vhdl_files_post: list[str] = None,
        use_build_cache: bool = False,
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
            extra_vhdl_files_post=extra_vhdl_files_post,
            use_build_cache=use_build_cache,
        )

        super().__init__(p)
        self._init_impl(p)

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
                port,
                None,
                ghdl_handle=self._sim.handle_by_name(f"{self._top_name}.{name}"),
                sim=self,
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

    async def rising_edge(self, signal: ProxyPort, /):
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

    async def falling_edge(self, signal: ProxyPort, /):
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

    async def any_edge(self, signal: ProxyPort, /):
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

    async def clock_cycles(self, signal: ProxyPort, num_cycles: int, rising=True):
        if isinstance(signal, std.Clock):
            signal = signal.signal()

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
