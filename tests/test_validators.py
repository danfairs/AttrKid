import attr
import hypothesis.strategies as st
import pytest
from hypothesis import given


def test_collection_of():
    from attrkid.validators import collection_of

    @attr.s
    class M:
        f = attr.ib(validator=collection_of(str))

    M(f=['a'])
    M(f=[])
    with pytest.raises(TypeError):
        M(f='a')
    with pytest.raises(TypeError):
        M(f=[1])
    with pytest.raises(TypeError):
        M(f=['a', 1])


@given(st.integers())
def test_one_of(n):
    from attrkid.validators import one_of

    @attr.s
    class M:
        f = attr.ib(validator=one_of(['x']))

    with pytest.raises(ValueError):
        M(f=n)

    M(f='x')


def test_composite():
    from attrkid.validators import one_of, all_of, instance_of

    @attr.s
    class M:
        f = attr.ib(validator=all_of(instance_of(int), one_of([1])))

    with pytest.raises(TypeError):
        M(f='x')
    with pytest.raises(ValueError):
        M(f=2)
    M(f=1)
