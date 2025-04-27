from cohdl import BitVector, Signed, Unsigned, Signal, Port, TypeQualifierBase


decay = TypeQualifierBase.decay


def load_all(*args):
    for arg in args:
        if isinstance(arg, _BaseProxyPort):
            arg._load()


class _BaseProxyPort(TypeQualifierBase):
    def __init__(
        self,
        entity_port: Signal[BitVector],
        root=None,
    ):
        self._Wrapped = Port.decay(entity_port)
        self._type = type(self._Wrapped)
        self._root = self if root is None else root

    def decay(self):
        return Port.decay(self._Wrapped)

    def __call__(self):
        return self

    def _is_root(self):
        return self._root is self

    def _to_type(self, inp):
        return self._type(inp)

    def copy(self):
        self._load()
        return self._Wrapped.copy()

    @property
    def signed(self):
        assert issubclass(self._type, BitVector)

        if issubclass(self._type, Signed):
            return self

        result = type(self)(self._Wrapped.signed, self._root)
        result._tmp_signed_parent = self
        result._load = self._load
        result._store = self._store
        return result

    @signed.setter
    def signed(self, value):
        assert (
            value is self or value._tmp_signed_parent is self
        ), "direct assignment to .signed property not allowed use '<<=' operator"

    @property
    def unsigned(self):
        assert issubclass(self._type, BitVector)

        if issubclass(self._type, Unsigned):
            return self

        result = type(self)(self._Wrapped.unsigned, self._root)
        result._tmp_unsigned_parent = self
        result._load = self._load
        result._store = self._store
        return result

    @unsigned.setter
    def unsigned(self, value):
        assert (
            value is self or value._tmp_unsigned_parent is self
        ), "direct assignment to .unsigned property not allowed use '<<=' operator"

    @property
    def bitvector(self):
        assert issubclass(self._type, BitVector)

        if not issubclass(self._type, (Signed, Unsigned)):
            return self

        result = type(self)(self._Wrapped.bitvector, self._root)
        result._tmp_bitvector_parent
        result._load = self._load
        result._store = self._store
        return result

    @bitvector.setter
    def bitvector(self, value):
        assert (
            value is self or value._tmp_bitvector_parent is self
        ), "direct assignment to .bitvector property not allowed use '<<=' operator"

    def __getitem__(self, arg):
        assert issubclass(self._type, BitVector)

        if isinstance(arg, slice):
            assert isinstance(arg.start, int)
            assert isinstance(arg.stop, int)
            assert arg.step is None
            result = type(self)(self._Wrapped[arg], self._root)
        else:
            assert isinstance(arg, int)
            result = type(self)(self._Wrapped[arg], self._root)

        # Replace load and store methods with version
        # of root object. They always update all bits of
        # a port even if they are accessed via a slice.
        result._load = self._load
        result._store = self._store

        return result

    def __setitem__(self, arg, value):
        pass

    def __ilshift__(self, src):
        if isinstance(src, _BaseProxyPort):
            src._load()
            src = src._Wrapped

        self._Wrapped._assign(src)
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
        return self._Wrapped.__bool__()

    def __index__(self):
        self._load()
        return self._Wrapped.__index__()

    def __eq__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__eq__(other)

    def __gt__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__gt__(other)

    def __lt__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__lt__(other)

    def __ge__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__ge__(other)

    def __invert__(self):
        self._load()
        return self._Wrapped.__invert__()

    def __le__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__le__(other)

    def __add__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__add__(other)

    def __sub__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__sub__(other)

    def __and__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__and__(other)

    def __or__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__or__(other)

    def __xor__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__xor__(other)

    def __matmul__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__matmul__(other)

    def __radd__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__radd__(other)

    def __rsub__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__rsub__(other)

    def __rand__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__rand__(other)

    def __ror__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__ror__(other)

    def __rxor__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__rxor__(other)

    def __rmatmul__(self, other):
        load_all(self, other)
        other = decay(other)
        return self._Wrapped.__rmatmul__(other)

    def resize(self, *args, **kwargs):
        return decay(self).resize(*args, **kwargs)

    def __str__(self):
        self._load()
        return str(self._Wrapped)

    def __repr__(self):
        self._load()
        return repr(self._Wrapped)

    #
    # abstract methods
    #

    def _load(self):
        raise AssertionError("abstract method called")

    def _store(self):
        raise AssertionError("abstract method called")
