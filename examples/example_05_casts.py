from cohdl import Entity, BitVector, Signed, Unsigned, Port, Null
from cohdl import std

from cohdl_sim import Simulator

from examples import _config

if not _config.use_ghdl_direct():
    from cohdl_sim import Simulator
else:
    # alternative simulator, direct ghdl access without cocotb
    from cohdl_sim.ghdl_sim import Simulator


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

    assert entity.result_add[0]
    assert entity.result_sub[0]


# The cast_vectors argument converts all BitVector ports
# to Signed or Unsigned, can be useful to reduce number of
# explicit casts in test code. Does not affect
# ports that are already Signed or Unsigned.
sim_unsigned = Simulator(MyEntity, cast_vectors=Unsigned)


@sim_unsigned.test
async def testbench_unsigned(entity: MyEntity):
    entity.inp_a <<= 7
    entity.inp_b <<= 10

    await sim.delta_step()

    for i in range(4):
        assert entity.result_add == 1
        assert entity.result_sub == 13

    entity.inp_a[0] <<= True

    await sim.delta_step()

    assert entity.result_add[0]
    assert entity.result_sub[0]


sim_signed = Simulator(MyEntity, cast_vectors=Signed)


@sim_signed.test
async def testbench_signed(entity: MyEntity):
    entity.inp_a <<= -3
    entity.inp_b <<= 6

    await sim.delta_step()

    for i in range(4):
        assert entity.result_add == 3
        assert entity.result_sub == 7

    entity.inp_a[0] <<= True

    await sim.delta_step()

    assert entity.result_add[0]
    assert entity.result_sub[0]
