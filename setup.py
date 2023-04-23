from setuptools import setup, find_packages

setup(
    name="cohdl_sim",
    version="0.1",
    description="Simulation support library for CoHDL, based on cocotb",
    author="Alexander Forster",
    author_email="alexander.forster123@gmail.com",
    packages=find_packages(exclude=["examples"]),
)
