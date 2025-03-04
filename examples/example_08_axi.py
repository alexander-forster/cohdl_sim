from __future__ import annotations

from cohdl import Null, BitVector
from cohdl import std

from cohdl.std.axi.axi4_light import addr_map_entity
from cohdl.std.reg import reg32

from cohdl_sim.axi.axi4_light import Axi4Light as AxiSim

from typing import Self

from examples import _config

if not _config.use_ghdl_direct():
    from cohdl_sim import Simulator
else:
    # alternative simulator, direct ghdl access without cocotb
    from cohdl_sim.ghdl_sim import Simulator


class InverterReg(reg32.Register):
    data: reg32.MemField[31:0]

    def _on_read_(self):
        return self(
            data=~self.data.val(),
        )


class ReverseReg(reg32.Register):
    data: reg32.MemField[31:0]

    def _on_read_(self):
        return self(
            data=std.reverse_bits(self.data.val()),
        )


class FifoReg(reg32.Register):
    data: reg32.Field[15:0]

    wr_cnt: reg32.UField[31:24, 0]
    rd_cnt: reg32.UField[23:16, 0]

    def _config_(self):
        self._fifo = std.Fifo[BitVector[16], 16]()

    def _on_write_(self, data: Self):
        self.wr_cnt <<= self.wr_cnt.val() + 1
        self._fifo.push(data.data.val())

    def _on_read_(self):
        if self._fifo.empty():
            return self(data=Null)
        else:
            self.rd_cnt <<= self.rd_cnt.val() + 1
            return self(data=self._fifo.pop())


class ExampleEntity(addr_map_entity()):

    reg_mem: reg32.MemWord[0x00]
    reg_inv: InverterReg[0x04]
    reg_rev: ReverseReg[0x08]
    reg_fifo: FifoReg[0x0C]


#
# test code for MyEntity
#

sim = Simulator(ExampleEntity, sim_args=["--vcd=waveform.vcd"])


@sim.test
async def testbench(entity: ExampleEntity):
    sim.init_inputs()
    entity.axi_reset <<= True

    sim.gen_clock(entity.axi_clk, std.MHz(100))

    ctx = entity.interface_context()
    con = entity.interface_connection()

    axi = AxiSim(sim, con)
    await sim.clock_edge(ctx.clk())

    print()
    print("registers 0, 4 and 8 demonstrate basic AXI operation")
    for addr in (0, 4, 8):
        print("addr = ", addr)
        for val in (3, 15, 63, 255):
            await axi.write(addr, val)
            print(await axi.read(addr))

    print()
    print("write and read fifo, counters are incremented")

    for val in range(8):
        await axi.write(0x0C, val)
        print(await axi.read(0x0C))

    print()
    print("write multiple values to fifo, then read them back")
    await axi.write_multiple([(0x0C, val) for val in (64, 16, 4, 1)])

    for data in await axi.read_multiple([0x0C] * 6):
        print(data)
