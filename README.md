# cohdl_sim

cohdl_sim is a simulation support library for [CoHDL](https://github.com/alexander-forster/cohdl). It is based on [cocotb](https://www.cocotb.org/) and works by turning CoHDL designs into VHDL and passing that code to cocotb test benches.

In addition cohdl_sim defines an abstraction layer so test code looks like CoHDL instead of cocotb.

---
## getting started

cohdl_sim requires Python3.10 or higher. You can install it by running

```shell
python3 -m pip install cohdl_sim
```

Since cohdl_sim is just a wrapper around [cocotb](https://www.cocotb.org/) you will also need one of the [supported VHDL simulators](https://docs.cocotb.org/en/stable/simulator_support.html). So far I have only used [GHDL](https://github.com/ghdl/ghdl).
