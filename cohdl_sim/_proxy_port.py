from cohdl import Bit, BitVector, Signal

from cocotb.handle import Freeze, Release
from cocotb.triggers import RisingEdge, FallingEdge, Edge, ClockCycles
from ._base_proxy_port import _BaseProxyPort


class ProxyPort(_BaseProxyPort):
    def __init__(
        self,
        entity_port: Signal[BitVector],
        root=None,
        cocotb_port=None,
    ):
        super().__init__(entity_port, root)

        # only set in root port
        self._cocotb_port = cocotb_port

    def _load(self):
        val = self._cocotb_port.value

        if issubclass(self._type, (Bit, BitVector)):
            self._Wrapped._assign(val.binstr.upper())
        else:
            raise AssertionError(f"type {type(self._type)} not supported")

    def _store(self):
        if isinstance(self._Wrapped, Bit):
            self._cocotb_port.value = bool(self._Wrapped)
        else:
            self._cocotb_port.value = self._Wrapped.unsigned.to_int()

    def freeze(self):
        assert (
            self._is_root()
        ), "freeze may only be used on port objects, not on sub-bits/slices"
        self._cocotb_port.value = Freeze()

    def release(self):
        assert (
            self._is_root()
        ), "release may only be used on port objects, not on sub-bits/slices"
        self._cocotb_port.value = Release()

    async def _rising_edge(self):
        if self._is_root():
            await RisingEdge(self._cocotb_port)
        else:
            self._load()
            prev = bool(self._Wrapped)

            while True:
                await Edge(self._cocotb_port)

                self._load()
                current = bool(self._Wrapped)

                if current and not prev:
                    return
                prev = current

    async def _falling_edge(self):
        if self._is_root():
            await FallingEdge(self._cocotb_port)
        else:
            self._load()
            prev = bool(self._Wrapped)

            while True:
                await Edge(self._root._cocotb_port)

                self._load()
                current = bool(self._Wrapped)

                if prev and not current:
                    return
                prev = current

    async def _edge(self):
        if self._is_root():
            await Edge(self._cocotb_port)
        else:
            self._load()
            prev = self._Wrapped.copy()

            while True:
                await Edge(self._root._cocotb_port)

                self._load()
                current = self._Wrapped.copy()

                if prev != current:
                    return
                prev = current

    async def _clock_cycles(self, num_cycles, rising=True):
        if self._is_root():
            await ClockCycles(self._cocotb_port, num_cycles, rising)
        else:
            if rising:
                for _ in num_cycles:
                    await self._rising_edge()
            else:
                for _ in num_cycles:
                    await self._falling_edge()

    def __await__(self):
        async def gen():
            while True:
                if self:
                    return
                await self._edge()

        return gen().__await__()
