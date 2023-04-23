# cohdl_sim example

In this  example we are using `cohdl_sim` to test a simple CoHDL design that takes two Bits as input and produces the result of both ored together.

```python
from cohdl import Entity, Bit, Port
from cohdl import std

class MyEntity(Entity):
    inp_a = Port.input(Bit)
    inp_b = Port.input(Bit)

    result = Port.output(Bit)

    def architecture(self):
        @std.concurrent
        def logic():
            self.result <<= self.inp_a | self.inp_b
```

`cohdl_sim` provides a single class Simulator that does three things:

1. it turns the given CoHDL entity into VHDL code
2. it starts `cocotb_test.run()` and executes all testbenches (marked with `Simulator.test`)
3. it wraps the dut object provided by cocotb in a proxy object so the simulation code looks like CoHDL



```python
from cohdl_sim import Simulator

sim = Simulator(MyEntity)

@sim.test
async def testbench_1(entity: MyEntity):
    entity.inp_a <<= True
    entity.inp_b <<= False

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
```