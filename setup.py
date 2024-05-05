from setuptools import setup, Extension, find_packages
import os

ext_modules = []

if os.name == "posix":
    import pybind11
    import subprocess

    status, ghdl_result = subprocess.getstatusoutput(
        "ghdl --libghdl-include-dir",
    )

    if status != 0:
        print("determining ghdl include directory failed")
        print("continuing without direct ghdl bindings")
    else:
        ext_modules = [
            Extension(
                "cohdl_sim_ghdl_interface",
                [
                    "cpp/cohdl_sim_ghdl_interface/main.cpp",
                    "cpp/cohdl_sim_ghdl_interface/ghdl_cohdl_interface.cpp",
                ],
                include_dirs=[pybind11.get_include(), ghdl_result],
                extra_compile_args=["-O0", "-g3"],
            ),
        ]

setup(
    name="cohdl_sim",
    version="0.2.0",
    author="Alexander Forster",
    author_email="alexander.forster123@gmail.com",
    description="Simulation support library for CoHDL, based on cocotb",
    ext_modules=ext_modules,
    packages=find_packages(exclude=["examples"]),
)
