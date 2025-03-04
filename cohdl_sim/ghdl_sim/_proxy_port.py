from cohdl_sim_ghdl_interface import ObjHandle

from cohdl import Signal, Bit, BitVector, Unsigned, Signed
from cohdl_sim._base_proxy_port import _BaseProxyPort


class ProxyPort(_BaseProxyPort):
    def __init__(
        self, entity_port: Signal, root=None, ghdl_handle: ObjHandle = None, sim=None
    ):
        super().__init__(entity_port, root)

        # the remaining members are None unless this is the root port
        self._handle = ghdl_handle
        self._sim = sim

    def _load(self):
        val = self._handle.get_binstr()

        if issubclass(self._type, (Bit, BitVector)):
            self._Wrapped._assign(val.upper())
        else:
            raise AssertionError(f"type {type(self._type)} not supported")

    def _store(self):
        if isinstance(self._Wrapped, (Unsigned, Signed)):
            self._handle.put_binstr(str(self._Wrapped.bitvector))
        else:
            self._handle.put_binstr(str(self._Wrapped))

    def __await__(self):
        async def gen():
            return await self._root._sim.value_true(self)

        return gen().__await__()
