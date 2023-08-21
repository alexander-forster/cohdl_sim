from cohdl import Entity, BitVector, Unsigned, Port, Null, Full
from cohdl import std

from cohdl_sim import Simulator


class MyEntity(Entity):
    inp_a = Port.input(BitVector[4])
    inp_b = Port.input(Unsigned[4])

    result_add = Port.output(BitVector[4])
    result_sub = Port.output(BitVector[4])

    def architecture(self):
        @std.concurrent
        def logic():
            self.result_add <<= self.inp_a.unsigned + self.inp_b
            self.result_sub <<= self.inp_a.unsigned - self.inp_b


#
# test code for MyEntity
#

sim = Simulator(MyEntity)


@sim.test
async def testbench(entity: MyEntity):
    entity.inp_a <<= Null
    entity.inp_b <<= Null

    await sim.delta_step()

    for i in range(4):
        # simulation code can use the unsigned/signed/bitvector
        # properties of signals to cast between vector types
        assert entity.result_add.unsigned == 0
        assert entity.result_sub.unsigned == 0

    entity.inp_a[0] <<= True

    await sim.delta_step()

    assert entity.result_add[0] == True
    assert entity.result_sub[0] == True
