import cohdl
from cohdl import std, Bit, BitVector, Unsigned, Signed, Port, Entity

from dataclasses import dataclass
from pathlib import Path
import json


def _store_port_info(port: cohdl.Port):
    port_type = std.base_type(port)

    dir = port.direction().name

    if issubclass(port_type, Bit):
        return {"type": "Bit", "dir": dir}
    if issubclass(port_type, cohdl.Boolean):
        return {"type": "Bool", "dir": dir}
    if issubclass(port_type, BitVector):
        w = port_type.width

        if issubclass(port_type, Unsigned):
            return {"type": "Unsigned", "width": w, "dir": dir}
        if issubclass(port_type, Unsigned):
            return {"type": "Signed", "width": w, "dir": dir}

        return {"type": "BitVector", "width": w, "dir": dir}

    raise AssertionError(f"invalid '{port_type=}'")


def _load_port_info(info: dict):
    dir = Port.Direction[info["dir"]]

    match info["type"]:
        case "Bit":
            t = Bit
        case "Bool":
            t = cohdl.Boolean
        case "Unsigned":
            t = Unsigned[info["width"]]
        case "Signed":
            t = Signed[info["width"]]
        case "BitVector":
            t = BitVector[info["width"]]
        case _:
            raise AssertionError(f"invalid '{info['type']=}'")

    return Port[t, dir]()


@dataclass
class CacheContent:
    vhdl_sources: list[str]


def write_cache_file(path: Path, entity: type[Entity], vhdl_sources: list[str]):
    top_ports = {
        name: _store_port_info(port) for name, port in entity._cohdl_info.ports.items()
    }

    with open(path, "w") as cache:
        json.dump(
            {"vhdl_sources": vhdl_sources, "top_ports": top_ports}, cache, indent=2
        )


def load_cache_file(path: Path, entity: type[Entity]) -> CacheContent:
    with open(path) as cache_file:
        cache = json.load(cache_file)

    vhdl_sources = cache["vhdl_sources"]
    top_ports = cache["top_ports"]

    for name, info in top_ports.items():
        if not hasattr(entity, name):
            std.add_entity_port(entity, _load_port_info(info), name=name)

    return CacheContent(vhdl_sources=vhdl_sources)
