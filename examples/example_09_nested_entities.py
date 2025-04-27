from __future__ import annotations

import cohdl
from cohdl import Null, BitVector, Port, Bit
from cohdl import std

from examples import _config

from random import randint

if not _config.use_ghdl_direct():
    from cohdl_sim import Simulator
else:
    # alternative simulator, direct ghdl access without cocotb
    from cohdl_sim.ghdl_sim import Simulator


class DelayData(cohdl.Entity):

    clk = Port.input(Bit)

    data_in = Port.input(BitVector[8])
    data_out = Port.output(BitVector[8])

    def architecture(self):

        @std.sequential(std.Clock(self.clk))
        def proc_delay():
            self.data_out <<= std.delayed(self.data_in, 3)


class MiddleEntity(cohdl.Entity):

    clk = Port.input(Bit)

    data_in1 = Port.input(BitVector[8])
    data_out1 = Port.output(BitVector[8])

    data_in2 = Port.input(BitVector[8])
    data_out2 = Port.output(BitVector[8])

    def architecture(self):

        DelayData(clk=self.clk, data_in=self.data_in1, data_out=self.data_out1)
        DelayData(clk=self.clk, data_in=self.data_in2, data_out=self.data_out2)


class OuterEntity(cohdl.Entity):

    clk = Port.input(Bit)

    data_in1 = Port.input(BitVector[8])
    data_out1 = Port.output(BitVector[8])

    data_in2 = Port.input(BitVector[8])
    data_out2 = Port.output(BitVector[8])

    def architecture(self):

        MiddleEntity(
            clk=self.clk,
            data_in1=self.data_in1,
            data_out1=self.data_out1,
            data_in2=self.data_in2,
            data_out2=self.data_out2,
        )


#
# test code for MyEntity
#

sim = Simulator(OuterEntity, sim_args=["--vcd=waveform.vcd"])


@sim.test
async def testbench(entity: OuterEntity):
    sim.init_inputs()
    sim.gen_clock(entity.clk, std.MHz(100))

    await sim.rising_edge(entity.clk)

    buffer_1 = [None, None, None, None]
    buffer_2 = [None, None, None, None]

    for nr in range(100):
        inp_1 = randint(0, 255)
        inp_2 = randint(0, 255)

        buffer_1.append(inp_1)
        buffer_2.append(inp_2)

        entity.data_in1.unsigned <<= inp_1
        entity.data_in2.unsigned <<= inp_2

        await sim.rising_edge(entity.clk)
        await sim.delta_step()

        if nr >= 3:
            assert buffer_1[-4] == entity.data_out1.unsigned
            assert buffer_2[-4] == entity.data_out2.unsigned
