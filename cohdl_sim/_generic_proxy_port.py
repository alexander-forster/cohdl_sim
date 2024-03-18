from cohdl import Bit, BitVector, Signed, Unsigned, Signal, Port, TypeQualifierBase


decay = TypeQualifierBase.decay


def load_all(*args):
    for arg in args:
        if isinstance(arg, _GenericProxyPort):
            arg._load()


_prev_property = None


class _GenericProxyPort(TypeQualifierBase):
    def __init__(
        self,
        entity_port: Signal[BitVector],
        root=None,
        uid: int | None = None,
    ):
        self._val = Port.decay(entity_port)
        self._type = type(self._val)
        self._root = self if root is None else root
        self._uid = id(self) if uid is None else uid

    def decay(self):
        return Port.decay(self._val)

    def __call__(self):
        return self

    def _is_root(self):
        return self._root is self

    def _to_type(self, inp):
        return self._type(inp)

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

        result = _GenericProxyPort(self._val.signed, self._root, self._uid)
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

        result = _GenericProxyPort(self._val.unsigned, self._root, self._uid)
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

        result = _GenericProxyPort(self._val.bitvector, self._root, self._uid)
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
            result = _GenericProxyPort(self._val[arg], self._root)
        else:
            assert isinstance(arg, int)
            result = _GenericProxyPort(self._val[arg], self._root)

        # Replace load and store methods with version
        # of root object. They always update all bits of
        # a port even if they are accessed via a slice.
        result._load = self._load
        result._store = self._store

        return result

    def __setitem__(self, arg, value):
        pass

    def __ilshift__(self, src):
        if isinstance(src, _GenericProxyPort):
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

    def resize(self, *args, **kwargs):
        return decay(self).resize(*args, **kwargs)

    def __str__(self):
        self._load()
        return str(self._val)

    def __repr__(self):
        self._load()
        return repr(self._val)

    def __await__(self):
        async def gen():
            return await self._root._sim.value_true(self)

        return gen().__await__()

    #
    # abstract methods
    #

    def _load(self):
        raise AssertionError("abstract method called")

    def _store(self):
        raise AssertionError("abstract method called")
