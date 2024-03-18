from cohdl_sim_ghdl_interface import GhdlInterface, ObjHandle

from cohdl import Signal, Port, Bit, BitVector, Unsigned, Signed
from cohdl_sim._generic_proxy_port import _GenericProxyPort
from cohdl.std import instance_check


class ProxyPort(_GenericProxyPort):
    def __init__(self, entity_port: Signal, ghdl_handle: ObjHandle, sim):
        assert not (
            instance_check(entity_port, Unsigned) and len(entity_port) >= 31
        ), "the ghdl simulator interface does not support unsigned ports with a width greater than 31"

        assert not (
            instance_check(entity_port, Signed) and len(entity_port) >= 32
        ), "the ghdl simulator interface does not support signed ports with a width greater than 32"

        super().__init__(entity_port)
        self._handle = ghdl_handle
        self._sim = sim

    def _load(self):
        val = self._handle.get_binstr()

        if issubclass(self._type, (Bit, BitVector)):
            self._val._assign(val.upper())
        else:
            raise AssertionError(f"type {type(self._type)} not supported")

    def _store(self):
        if isinstance(self._val, (Unsigned, Signed)):
            self._handle.put_integer(self._val.to_int())
        else:
            self._handle.put_binstr(str(self._val))
