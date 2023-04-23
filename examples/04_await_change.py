from cohdl import Entity, Bit, Unsigned, Port, Null, Full
from cohdl import std

from cohdl_sim import Simulator


class MyEntity(Entity):
    clk = Port.input(Bit)
    reset = Port.input(Bit)

    cnt = Port.output(Unsigned[4], default=0)

    def architecture(self):
        @std.sequential(std.Clock(self.clk), std.Reset(self.reset))
        def proc():
            self.cnt <<= self.cnt + 1


sim = Simulator(MyEntity, sim_args=["--vcd=waveform.vcd"])


@sim.test
async def testbench_gen_clk(entity: MyEntity):
    sim.gen_clock(entity.clk, std.GHz(1))

    entity.reset <<= True
    await sim.rising_edge(entity.clk)
    entity.reset <<= False

    # wait until value of entity.cnt changes
    # and check if the change was an increment as expected
    for cnt in range(0, 10):
        assert entity.cnt == cnt
        await sim.value_change(entity.cnt)

    # sim.value_true/sim.value_false
    # stop the coroutine execution until
    # the argument becomes truthy/falsy
    for _ in range(5):
        # wait until entity.cnt == 0
        await sim.value_false(entity.cnt)
        # wait until entity.cnt != 0
        await sim.value_true(entity.cnt)
        # wait until entit.cnt[2] != 0
        await sim.value_true(entity.cnt[2])

    # sim.value_true can be replaced with a plain await expression
    # it is not possible implement sim.value_false in this way
    for _ in range(5):
        # wait until entity.cnt == 0
        await sim.value_false(entity.cnt)
        # wait until entity.cnt != 0
        await entity.cnt
        # wait until entity.cnt[3] != 0
        await entity.cnt[3]
