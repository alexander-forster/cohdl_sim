from cohdl import Entity, BitVector, Port, Null, Full
from cohdl import std

from examples import _config

if not _config.use_ghdl_direct():
    from cohdl_sim import Simulator
else:
    # alternative simulator, direct ghdl access without cocotb
    from cohdl_sim.ghdl_sim import Simulator


class MyEntity(Entity):
    inp_a = Port.input(BitVector[4])
    inp_b = Port.input(BitVector[4])

    result_or = Port.output(BitVector[4])
    result_and = Port.output(BitVector[4])
    result_concat = Port.output(BitVector[8])

    def architecture(self):
        @std.concurrent
        def logic():
            self.result_or <<= self.inp_a | self.inp_b
            self.result_and <<= self.inp_a & self.inp_b
            self.result_concat <<= self.inp_a @ self.inp_b


#
# test code for MyEntity
#

sim = Simulator(MyEntity)


@sim.test
async def testbench(entity: MyEntity):
    entity.inp_a <<= Null
    entity.inp_b <<= Full

    await sim.delta_step()

    for i in range(4):
        # simulation code can read and write slices of ports
        assert entity.result_or[i]
        assert not entity.result_and[i]
        assert entity.result_concat[i]
        assert not entity.result_concat[i + 4]

    entity.inp_a[0] <<= True

    await sim.delta_step()

    assert entity.result_or[0]
    assert entity.result_and[0]
    assert entity.result_concat[4]
