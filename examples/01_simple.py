from cohdl import Entity, Bit, Port
from cohdl import std

from cohdl_sim import Simulator


class MyEntity(Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.result <<= self.inp_a | self.inp_b


#
# test code for MyEntity
#

# The simulator object generates VHDL from
# the given entity and forwards it to the test benches.
# You can customize the output directory (default=./build)
# and the simulator to use (default=ghdl).
# All other arguments are forwarded to cocotb_test.simulator.run()
# (see https://github.com/themperek/cocotb-test)
sim = Simulator(MyEntity)


# Mark coroutines with sim.test to turn them into test benches.
# The given argument is a proxy object based on the tested entity
# Port assignments and reads are forwarded to the simulator.
@sim.test
async def testbench_1(entity: MyEntity):
    # cohdl_sim is a wrapper around cocotb
    # so test code looks like cohdl
    entity.inp_a <<= True
    entity.inp_b <<= False

    # run one delta step to update
    # output according to input
    await sim.delta_step()

    assert entity.result == True


@sim.test
async def testbench_2(entity: MyEntity):
    for a in (False, True):
        for b in (False, True):
            entity.inp_a <<= a
            entity.inp_b <<= b

            await sim.delta_step()

            assert entity.result == (a | b)
