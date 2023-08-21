from cohdl import Bit, BitVector, Signed, Unsigned, Signal, Port, TypeQualifierBase

from cocotb.handle import Freeze, Release
from cocotb.triggers import RisingEdge, FallingEdge, Edge, ClockCycles


def to_cocotb(cohdl_val):
    if isinstance(cohdl_val, Bit):
        return bool(cohdl_val)
    return cohdl_val.unsigned.to_int()


decay = TypeQualifierBase.decay


def load_all(*args):
    for arg in args:
        if isinstance(arg, ProxyPort):
            arg._load()


_prev_property = None


class ProxyPort(TypeQualifierBase):
    def __init__(
        self,
        entity_port: Signal[BitVector],
        cocotb_port,
        is_root=True,
        uid: int | None = None,
    ):
        self._val = Port.decay(entity_port)
        self._type = type(self._val)
        self._root = is_root
        self._cocotb_port = cocotb_port
        self._uid = id(self) if uid is None else uid

    def decay(self):
        return Port.decay(self._val)

    def __call__(self):
        return self

    def _is_root(self):
        return self._root

    def _to_type(self, inp):
        return self._type(inp)

    def _load(self):
        val = self._cocotb_port.value

        if issubclass(self._type, (Bit, BitVector)):
            self._val._assign(val.binstr.upper())
        else:
            raise AssertionError(f"type {type(self._type)} not supported")

    def _store(self):
        if isinstance(self._val, Bit):
            self._cocotb_port.value = bool(self._val)
        else:
            self._cocotb_port.value = self._val.unsigned.to_int()

    def copy(self):
        self._load()
        return self._val.copy()

    @property
    def signed(self):
        global _prev_property
        assert issubclass(self._type, BitVector)

        if issubclass(self._type, Signed):
            _prev_property = self
            return self

        result = ProxyPort(self._val.signed, self._cocotb_port, False, self._uid)
        result._load = self._load
        result._store = self._store
        _prev_property = result
        return result

    @signed.setter
    def signed(self, value):
        assert (
            value._uid is self._uid
        ), "direct assignment to .signed property not allowed use '<<=' operator"

    @property
    def unsigned(self):
        global _prev_property
        assert issubclass(self._type, BitVector)

        if issubclass(self._type, Unsigned):
            _prev_property = self
            return self

        result = ProxyPort(self._val.unsigned, self._cocotb_port, False, self._uid)
        result._load = self._load
        result._store = self._store
        _prev_property = result
        return result

    @unsigned.setter
    def unsigned(self, value):
        assert (
            value._uid is self._uid
        ), "direct assignment to .unsigned property not allowed use '<<=' operator"

    @property
    def bitvector(self):
        global _prev_property
        assert issubclass(self._type, BitVector)

        if not issubclass(self._type, (Signed, Unsigned)):
            _prev_property = self
            return self

        result = ProxyPort(self._val.bitvector, self._cocotb_port, False, self._uid)
        result._load = self._load
        result._store = self._store
        _prev_property = result
        return result

    @bitvector.setter
    def bitvector(self, value):
        assert (
            value._uid is self._uid
        ), "direct assignment to .bitvector property not allowed use '<<=' operator"

    def __getitem__(self, arg):
        assert issubclass(self._type, BitVector)

        if isinstance(arg, slice):
            assert isinstance(arg.start, int)
            assert isinstance(arg.stop, int)
            assert arg.step is None
            result = ProxyPort(self._val[arg], self._cocotb_port, False)
        else:
            assert isinstance(arg, int)
            result = ProxyPort(self._val[arg], self._cocotb_port, False)

        # Replace load and store methods with version
        # of root object. They always update all bits of
        # a port even if they are accessed via a slice.
        result._load = self._load
        result._store = self._store

        return result

    def __setitem__(self, arg, value):
        pass

    def __ilshift__(self, src):
        if isinstance(src, ProxyPort):
            src = src._val

        self._val._assign(src)
        self._store()
        return self

    @property
    def next(self):
        raise AssertionError("reading from .next property not allowed")

    @next.setter
    def next(self, value):
        self <<= value

    @property
    def type(self):
        return self._type

    def __bool__(self):
        self._load()
        return self._val.__bool__()

    def __index__(self):
        self._load()
        return self._val.__index__()

    def __eq__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__eq__(other)

    def __gt__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__gt__(other)

    def __lt__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__lt__(other)

    def __ge__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__ge__(other)

    def __invert__(self):
        self._load()
        return self._val.__invert__()

    def __le__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__le__(other)

    def __add__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__add__(other)

    def __sub__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__sub__(other)

    def __and__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__and__(other)

    def __or__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__or__(other)

    def __xor__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__xor__(other)

    def __matmul__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__matmul__(other)

    def __radd__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__radd__(other)

    def __rsub__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__rsub__(other)

    def __rand__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__rand__(other)

    def __ror__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__ror__(other)

    def __rxor__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__rxor__(other)

    def __rmatmul__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._val.__rmatmul__(other)

    def __str__(self):
        self._load()
        return str(self._val)

    def __repr__(self):
        self._load()
        return repr(self._val)

    def freeze(self):
        assert (
            self._is_root()
        ), "freeze may only be used on port objects, not on sub-bits/slices"
        self._cocotb_port.value = Freeze()

    def release(self):
        assert (
            self._is_root()
        ), "release may only be used on port objects, not on sub-bits/slices"
        self._cocotb_port.value = Release()

    async def _rising_edge(self):
        if self._root:
            await RisingEdge(self._cocotb_port)
        else:
            self._load()
            prev = bool(self._val)

            while True:
                await Edge(self._cocotb_port)

                self._load()
                current = bool(self._val)

                if current and not prev:
                    return
                prev = current

    async def _falling_edge(self):
        if self._root:
            await FallingEdge(self._cocotb_port)
        else:
            self._load()
            prev = bool(self._val)

            while True:
                await Edge(self._cocotb_port)

                self._load()
                current = bool(self._val)

                if prev and not current:
                    return
                prev = current

    async def _edge(self):
        if self._root:
            await Edge(self._cocotb_port)
        else:
            self._load()
            prev = self._val.copy()

            while True:
                await Edge(self._cocotb_port)

                self._load()
                current = self._val.copy()

                if prev != current:
                    return
                prev = current

    async def _clock_cycles(self, num_cycles, rising=True):
        if self._root:
            await ClockCycles(self._cocotb_port, num_cycles, rising)
        else:
            if rising:
                for _ in num_cycles:
                    await self._rising_edge()
            else:
                for _ in num_cycles:
                    await self._falling_edge()

    def __await__(self):
        async def gen():
            while True:
                if self:
                    return
                await self._edge()

        return gen().__await__()

    def resize(self, *args, **kwargs):
        return decay(self).resize(*args, **kwargs)
