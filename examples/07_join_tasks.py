from cohdl import Entity, Unsigned, Port, Bit
from cohdl import std

from cohdl_sim import Simulator

# alternative simulator, direct ghdl access without cocotb
# from cohdl_sim.ghdl_sim import Simulator


# entity that provides three example tasks
# with different, configurable durations
class MyEntity(Entity):
    clk = Port.input(Bit)

    a_start = Port.input(Bit)
    a_duration = Port.input(Unsigned[8])
    a_done = Port.output(Bit, default=False)

    b_start = Port.input(Bit)
    b_duration = Port.input(Unsigned[8])
    b_done = Port.output(Bit, default=False)

    c_start = Port.input(Bit)
    c_duration = Port.input(Unsigned[8])
    c_done = Port.output(Bit, default=False)

    def architecture(self):
        @std.sequential(std.Clock(self.clk))
        async def proc_wait():
            await self.a_start
            await std.wait_for(self.a_duration)
            self.a_done ^= True

        @std.sequential(std.Clock(self.clk))
        async def proc_wait():
            await self.b_start
            await std.wait_for(self.b_duration)
            self.b_done ^= True

        @std.sequential(std.Clock(self.clk))
        async def proc_wait():
            await self.c_start
            await std.wait_for(self.c_duration)
            self.c_done ^= True


#
# test code for MyEntity
#

sim = Simulator(MyEntity)


@sim.test
async def testbench(entity: MyEntity):
    sim.init_inputs()
    sim.gen_clock(entity.clk, std.MHz(100))

    await sim.rising_edge(entity.clk)

    async def wait_task(prefix, delay=10):
        start = getattr(entity, f"{prefix}_start")
        duration = getattr(entity, f"{prefix}_duration")
        done = getattr(entity, f"{prefix}_done")

        print("start: ", prefix)
        duration <<= delay
        start <<= True
        await sim.rising_edge(entity.clk)
        start <<= False
        await sim.value_true(done)
        print("done: ", prefix)

    # start three tasks with different durations
    # then wait until all are done

    task_a = sim.start_soon(wait_task("a", 10))
    task_b = sim.start_soon(wait_task("b", 5))
    task_c = sim.start_soon(wait_task("c", 3))

    await task_a.join()
    await task_b.join()
    await task_c.join()
