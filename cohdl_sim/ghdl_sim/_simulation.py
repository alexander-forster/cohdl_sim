from cohdl import Entity
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


def n(i):
    return i


def x(i):
    global_alive_list.append(i)
    return i


def l(x):
    x.__del__ = lambda: print("DEL")

    return x


class Simulator:
    def __init__(self, entity: type[Entity], *, build_dir: str = "build", mkdir=True):
        build_dir = Path(build_dir)

        if not os.path.exists(build_dir):
            if mkdir:
                os.makedirs(build_dir, exist_ok=True)
            else:
                raise AssertionError(f"target directory '{build_dir}' does not exist")

        lib = std.VhdlCompiler.to_vhdl_library(entity)

        top_name = lib.top_entity().name()
        entity_names = [sub.name() for sub in lib._entities]

        lib.write_dir(build_dir)

        vhdl_sources = [f"{build_dir}/{name}.vhd" for name in entity_names]

        self._entity = entity
        self._simlib = prepare_ghdl_simulation(
            vhdl_sources, top_name, build_dir, copy_files=False
        )

        self._top_name = top_name
        self._sim = GhdlInterface()

        self._tb = None
        self._current_coro = None

    def _initial_fn(self):
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

        for name, port in self._entity._info.ports.items():
            setattr(
                EntityProxy,
                name,
                ProxyPort(
                    port, self._sim.handle_by_name(f"{self._top_name}.{name}"), sim=self
                ),
            )

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

    def test(self, testbench):
        async def tb_wrapper(entity):
            await testbench(entity)
            self._sim.finish_simulation()

        self._tb = tb_wrapper
        self._sim.cleanup()

        global_alive_list.append(self._sim.add_startup_function(self._startup_function))
        self._sim.start(str(self._simlib), ["--wave=wave.ghw"])
        self._sim.stop()

    async def _wait_picoseconds(self, picos: int):
        with x(
            self._sim.cb_delay(
                partial(self._continue, self._current_coro, name="picos"), picos
            )
        ):
            await _suspend

    async def wait(self, duration: std.Duration):
        await self._wait_picoseconds(int(duration.picoseconds()))

    async def delta_step(self):
        with x(self._sim.cb_delay(partial(self._continue, self._current_coro), 1)):
            await _suspend

    async def rising_edge(self, signal: ProxyPort):
        with n(
            self._sim.cb_value_change(
                signal._root._handle,
                partial(self._continue, self._current_coro, name="rising_edge"),
            )
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if (not prev_state) and new_state:
                    await self.delta_step()
                    return
                prev_state = new_state

    async def falling_edge(self, signal: ProxyPort):
        with self._sim.cb_value_change(
            signal._root._handle,
            partial(self._continue, self._current_coro, name="falling_edge"),
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if prev_state and not new_state:
                    await self.delta_step()
                    return
                prev_state = new_state

    async def any_edge(self, signal: ProxyPort):
        with self._sim.cb_value_change(
            signal._root._handle,
            partial(self._continue, self._current_coro, name="any_edge"),
        ):
            prev_state = signal.copy()

            while True:
                await _suspend
                new_state = signal.copy()

                if prev_state != new_state:
                    await self.delta_step()
                    return
                prev_state = new_state

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
                            await self.delta_step()
                            return

                    prev_state = new_state
            else:
                while True:
                    await _suspend
                    new_state = signal.copy()

                    if prev_state and not new_state:
                        num_cycles -= 1
                        if num_cycles == 0:
                            await self.delta_step()
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
        self.start_soon(coro)
        await self.delta_step()

    def start_soon(self, coro):
        async def wrapper():
            await self.delta_step()
            self._continue(coro)

        self._continue(wrapper())

    def gen_clock(self, clk: ProxyPort, period: std.Duration, start_state=False):
        if isinstance(period, std.Frequency):
            period = period.period()

        half = int(period.picoseconds()) // 2

        async def thread():
            nonlocal clk

            while True:
                clk <<= start_state
                await self._wait_picoseconds(half)
                clk <<= not start_state
                await self._wait_picoseconds(half)

        self.start_soon(thread())
