from __future__ import annotations

from cohdl import std, Null, Full, BitVector, Unsigned
from cohdl_sim import Simulator


class Axi4Light:
    def __init__(self, sim: Simulator, con: std.axi.axi4_light.Axi4Light):
        self._con = con
        self._sim = sim

    async def read(self, address: int):
        con = self._con
        sim = self._sim

        addr = con.rdaddr
        data = con.rddata

        addr.araddr <<= address
        data.ready <<= False

        addr.valid <<= True
        await sim.true_on_clk(con.clk, addr.ready, timeout=10)
        addr.valid <<= False

        data.ready <<= True
        await sim.true_on_clk(con.clk, data.valid, timeout=10)
        data.ready <<= False

        return data.rdata.copy()

    async def read_multiple(self, addresses: list[int]):
        con = self._con
        sim = self._sim

        result = []

        addr = con.rdaddr
        data = con.rddata

        async def send_req():
            addr.valid <<= True
            for addr_val in addresses:
                addr.araddr.unsigned <<= addr_val
                await sim.true_on_clk(con.clk, addr.ready)
            addr.valid <<= False

        sim.start_soon(send_req())

        data.ready <<= True

        for _ in addresses:
            await sim.true_on_clk(con.clk, data.valid)
            result.append(data.rdata.copy())

        data.ready <<= False

        return result

    async def write(self, address: int, value: BitVector, wstrb: BitVector = Full):
        con = self._con
        sim = self._sim

        addr = con.wraddr
        data = con.wrdata
        resp = con.wrresp

        addr.awaddr <<= address
        addr.valid <<= True
        data.wdata <<= Unsigned[32](value)
        data.wstrb <<= wstrb
        data.valid <<= True
        resp.ready <<= False

        ack_addr = False
        ack_data = False

        while not (ack_addr and ack_data):
            await sim.clock_edge(con.clk)

            if not ack_addr and addr.ready:
                ack_addr = True
                addr.valid <<= False

            if not ack_data and data.ready:
                ack_data = True
                data.valid <<= False
                data.wdata <<= Null
                data.wstrb <<= Null

        resp.ready <<= True

        await sim.true_on_clk(con.clk, resp.valid, timeout=10)
        resp.ready <<= False

        await sim.clock_edge(con.clk)

        return resp.bresp.copy()

    async def write_multiple(self, addr_value: list[tuple[int, int]]):
        con = self._con
        sim = self._sim

        addr = con.wraddr
        data = con.wrdata
        resp = con.wrresp

        async def send_addr():
            for wraddr, _ in addr_value:
                addr.awaddr.unsigned <<= wraddr
                addr.valid <<= True
                await sim.true_on_clk(con.clk, addr.ready)

            addr.valid <<= False

        async def send_data():

            await sim.clock_cycles(con.clk, num_cycles=5)

            data.wstrb <<= Full
            for _, wrdata in addr_value:
                data.wdata.unsigned <<= wrdata
                data.valid <<= True
                await sim.true_on_clk(con.clk, data.ready)

            data.valid <<= False
            data.wstrb <<= Null

        result = []

        sim.start_soon(send_addr())
        sim.start_soon(send_data())

        resp.ready <<= True
        for _ in addr_value:
            await sim.true_on_clk(con.clk, resp.valid)
            result.append(resp.bresp.copy())

        resp.ready <<= False

        return result
