from cohdl_sim_ghdl_interface import ObjHandle

from cohdl import Signal, Bit, BitVector, Unsigned, Signed
from cohdl_sim._generic_proxy_port import _GenericProxyPort


class ProxyPort(_GenericProxyPort):
    def __init__(self, entity_port: Signal, ghdl_handle: ObjHandle, sim):
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
            self._handle.put_binstr(str(self._val.bitvector))
        else:
            self._handle.put_binstr(str(self._val))
