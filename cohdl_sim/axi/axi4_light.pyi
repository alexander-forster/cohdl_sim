from __future__ import annotations

from cohdl import std, BitVector, Unsigned
from cohdl_sim import Simulator

class Axi4Light:
    def __init__(self, sim: Simulator, con: std.axi.axi4_light.Axi4Light):
        """ """

    async def read(self, address: int | Unsigned) -> BitVector:
        """
        Send one read request, wait for the response and
        return the received data.
        """

    async def read_multiple(self, addresses: list[int | Unsigned]) -> list[BitVector]:
        """
        Send multiple read requests, wait for all responses and
        return them in a list.
        """

    async def write(self, address: int | Unsigned, value: BitVector):
        """ """

    async def write_multiple(self, addr_value: list[tuple[int | Unsigned, BitVector]]):
        """ """
