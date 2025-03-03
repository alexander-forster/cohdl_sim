from cohdl import Entity, Bit, Unsigned, Port
from cohdl import std

from cohdl_sim import Simulator

# alternative simulator, direct ghdl access without cocotb
# from cohdl_sim.ghdl_sim import Simulator


class MyEntity(Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    cnt = Port.output(Unsigned[8], default=0)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        def proc():
            self.cnt <<= self.cnt + 1


#
# test code for MyEntity
#

# Simulator forwards arguments to cocotb_test.simulator.run().
# This can be used to pass arguments to the simulator (default=ghdl).
# For example the flag --vcd generates a value dump.
sim = Simulator(MyEntity, sim_args=["--vcd=waveform.vcd"])


@sim.test
async def testbench_cnt(entity: MyEntity):
    entity.clk <<= False
    entity.reset <<= True

    # wait for 1 ns of simulation time
    await sim.wait(std.ns(1))
    entity.clk <<= True
    await sim.wait(std.ns(1))

    # reset complete after rising edge on entity.clk
    entity.reset <<= False
    entity.clk <<= False

    # generate 10 clock cycles and check that entity.cnt is incremented
    for cnt in range(0, 10):
        assert entity.cnt == cnt

        await sim.wait(std.ns(1))
        entity.clk <<= True
        await sim.wait(std.ns(1))
        entity.clk <<= False


@sim.test
async def testbench_gen_clk(entity: MyEntity):
    # gen_clk starts a parallel task that
    # generates a clock signal of the requested frequency
    sim.gen_clock(entity.clk, std.GHz(1))

    # reset design by setting the reset signal to true
    # and waiting for a rising edge on entity.clk
    entity.reset <<= True
    await sim.rising_edge(entity.clk)
    await sim.delta_step()
    entity.reset <<= False

    # check entity.cnt for 10 clock cycles
    for cnt in range(0, 10):
        assert entity.cnt == cnt

        await sim.rising_edge(entity.clk)
        await sim.delta_step()
