import os

from abc import ABC, abstractmethod

from pathlib import Path

from cohdl import Entity
from cohdl import std
from cohdl import Null

from ._proxy_port import ProxyPort


class Task:
    async def join(self): ...


class _GenericParams:
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
        self.entity = entity
        self.build_dir = Path(build_dir)

        self.simulator = simulator
        self.sim_dir = self.build_dir / sim_dir
        self.vhdl_dir = self.build_dir / vhdl_dir

        self.sim_args = [] if sim_args is None else sim_args
        self.extra_env = {} if extra_env is None else extra_env
        self.extra_vhdl_files = [] if extra_vhdl_files is None else extra_vhdl_files
        self.extra_vhdl_files_post = (
            [] if extra_vhdl_files_post is None else extra_vhdl_files_post
        )

        self.cache_file = self.build_dir / ".build-cache.json"

        # use cache file requested and available, rebuild it otherwise
        self.use_build_cache = use_build_cache and self.cache_file.exists()

        self.cast_vectors = cast_vectors

        for dir in (self.build_dir, self.sim_dir, self.vhdl_dir):
            if not os.path.exists(dir):
                os.makedirs(dir, exist_ok=True)


class _BaseSimulator(ABC):
    def __init__(self, params: _GenericParams):
        self._params = params

    @abstractmethod
    def test(self, testbench, /): ...

    @abstractmethod
    async def wait(self, duration: std.Duration, /): ...

    @abstractmethod
    async def delta_step(self): ...

    @abstractmethod
    async def rising_edge(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def falling_edge(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def any_edge(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def clock_cycles(
        self, signal: ProxyPort | std.Clock, num_cycles: int, rising=True
    ): ...

    @abstractmethod
    async def value_change(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def value_true(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def value_false(self, signal: ProxyPort, /): ...

    @abstractmethod
    async def start(self, coro, /) -> Task: ...

    @abstractmethod
    def start_soon(self, coro, /) -> Task: ...

    @abstractmethod
    def gen_clock(
        self, clk, period_or_frequency: std.Duration = None, /, start_state=False
    ): ...

    def init_inputs(self, init_val=Null, /):
        for port in self._input_ports.values():
            port <<= init_val

    def init_outputs(self, init_val=Null, /):
        for port in self._output_ports.values():
            port <<= init_val

    def init_inouts(self, init_val=Null, /):
        for port in self._inout_ports.values():
            port <<= init_val

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
