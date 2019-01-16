import datetime
import json
import sys

import attr
import decimal
import pytest
import pytz

from attr.validators import instance_of


@pytest.fixture()
def dt():
    return datetime.datetime(2017, 11, 13, 15, 12, 0, tzinfo=pytz.utc)


@attr.s
class TargetModel:
    pass


def test_from_dict_simple():
    from attrkid import from_dict

    @attr.s
    class M:
        a = attr.ib()

    m = from_dict(M, {'a': 1})
    assert 1 == m.a


def test_from_dict_datetime(dt):
    from attrkid import from_dict
    from attrkid.fields import datetime_field

    @attr.s
    class M:
        a = datetime_field()

    m = from_dict(M, {'a': '2017-11-13T15:12:00'})
    assert dt == m.a


def test_from_dict_defaults():
    from attrkid import from_dict

    @attr.s
    class M:
        a = attr.ib()

    m = from_dict(M, {}, defaults={'a': 1})
    assert 1 == m.a

    m = from_dict(M, {'a': 2}, defaults={'a': 1})
    assert 2 == m.a


def test_from_dict_object_defaults():
    from attrkid import from_dict
    from attrkid.fields import object_field

    @attr.s
    class L:
        b = attr.ib()

    @attr.s
    class M:
        a = object_field(L)

    defaults = {'a': L(b='hello')}
    m = from_dict(M, {}, defaults=defaults)
    assert M(a=L(b='hello')) == m


def test_from_dict_nested_defaults():
    from attrkid import from_dict
    from attrkid.fields import int_field, object_field

    @attr.s
    class A:
        f = int_field()

    @attr.s
    class B:
        a = object_field(A)

    defaults = {'a': {'f': 1}}

    m = from_dict(B, {}, defaults=defaults)
    assert B(a=A(f=1)) == m


def test_from_dict_field_defaults():
    from attrkid import from_dict
    from attrkid.validators import instance_of

    @attr.s
    class M:
        a = attr.ib(default=1, validator=instance_of(int))

    m = from_dict(M, {})
    assert 1 == m.a


def test_nested():
    from attrkid import from_dict
    from attrkid.fields import list_field

    @attr.s
    class X:
        t = attr.ib()

    @attr.s
    class M:
        xs = list_field(X)

    xs = [{'t': 1}, {'t': 2}]
    xs_raw = json.dumps(xs)
    m = from_dict(M, {'xs': xs_raw})
    assert [X(t=1), X(t=2)] == m.xs

    # Should also work if xs is actually a decoded list
    m = from_dict(M, {'xs': xs})
    assert [X(t=1), X(t=2)] == m.xs


def test_list_primitives():
    from attrkid import from_dict
    from attrkid.fields import list_field

    @attr.s
    class M:
        xs = list_field(int)

    m = from_dict(M, {'xs': [1, 2, 3]})
    assert M(xs=[1, 2, 3]) == m


def test_set_field():
    from attrkid import from_dict
    from attrkid.fields import set_field

    @attr.s
    class M:
        xs = set_field(int)

    m = from_dict(M, {'xs': [1, 2, 2, 3]})
    assert M(xs={1, 2, 3}) == m


def test_set_field_object():
    from attrkid import from_dict, to_dict
    from attrkid.fields import set_field, int_field

    @attr.s(slots=True, frozen=True, hash=True)
    class A:
        f = int_field()

    @attr.s
    class M:
        xs = set_field(A)

    m = M(xs={A(f=3)})
    d = to_dict(m)
    assert m == from_dict(M, d)


def test_validate_set_field():
    from attrkid.fields import set_field

    @attr.s
    class M:
        xs = set_field(int)

    with pytest.raises(TypeError) as exc:
        M(xs={'a'})

    message = exc.value.args[0]
    assert message.startswith('`a` is not of type'), message


def test_list_field_validator(mocker):
    from attrkid.fields import list_field

    v = mocker.MagicMock()
    v.side_effect = ValueError()

    @attr.s
    class M:
        xs = list_field(int, validator=v)

    with pytest.raises(ValueError):
        M(xs=[1])


def test_missing():
    from attrkid import from_dict
    from attrkid.fields import list_field

    @attr.s
    class X:
        t = attr.ib()

    @attr.s
    class M:
        xs = list_field(X)

    m = from_dict(M, {})
    assert [] == m.xs


def test_list_default():
    from attrkid.fields import list_field

    @attr.s
    class M:
        xs = list_field(str)

    m = M()
    assert [] == m.xs


def test_bad_type():
    from attrkid import from_dict
    from attrkid.exceptions import ValidationError
    from attrkid.validators import instance_of

    @attr.s
    class M:
        v = attr.ib(validator=instance_of(int))

    with pytest.raises(ValidationError):
        from_dict(M, {'v': '1'})


def test_to_dict(dt):
    from attrkid import to_dict, from_dict
    from attrkid.fields import datetime_field, list_field
    from attrkid.options import SerdeOptions

    @attr.s
    class X:
        f = attr.ib()

    @attr.s
    class M:
        s = attr.ib(validator=instance_of(str))
        i = attr.ib(validator=instance_of(int))
        nullable = attr.ib()
        d = datetime_field()
        lst1 = list_field(int)
        lst2 = list_field(X)

    m = M(
        s='hello',
        i=42,
        d=dt,
        lst1=[1, 2, 3],
        lst2=[X(f=1)],
        nullable=None,
    )
    options = SerdeOptions(omit_null_values=False)
    actual = to_dict(m, options=options)
    expected = {
        's': 'hello',
        'i': 42,
        'd': '2017-11-13T15:12:00.000000Z',
        'lst1': [1, 2, 3],
        'lst2': [{
            'f': 1
        }],
        'nullable': None
    }
    assert expected == actual

    expected_nullable = {
        's': 'hello',
        'i': 42,
        'd': '2017-11-13T15:12:00.000000Z',
        'lst1': [1, 2, 3],
        'lst2': [{
            'f': 1
        }],
    }
    actual_nullable = to_dict(m)
    assert expected_nullable == actual_nullable

    # Check we can round-trip
    m1 = from_dict(M, actual)
    assert m == m1

    m2 = from_dict(M, actual_nullable)
    assert m == m2


def test_primary_key():
    from attrkid.fields import primary_key
    from attrkid.reflect import (primary_key_for, primary_key_value_for)

    @attr.s
    class M:
        k = primary_key(int)
        f = attr.ib()

    fields = attr.fields(M)
    assert fields.k is primary_key_for(M)

    m = M(k=1, f=2)
    assert 1 == primary_key_value_for(m)


def test_primary_key_auto():
    from attrkid.fields import primary_key
    from attrkid.reflect import (primary_key_for, primary_key_value_for)

    @attr.s
    class M:
        f = attr.ib()
        k = primary_key(auto=True)

    fields = attr.fields(M)
    assert fields.k is primary_key_for(M)

    m = M(f=2)
    pk = primary_key_value_for(m)
    assert bool(pk)

    @attr.s
    class N:
        k = primary_key(str, auto=True, auto_func=lambda: "hello")

    n = N()
    assert 'hello' == primary_key_value_for(n)


def test_optional_datetime_field():
    from attrkid.fields import datetime_field

    @attr.s
    class M:
        f = datetime_field(is_optional=True)

    m = M(f=None)
    assert m.f is None


def test_optional_extra_validator():
    from attrkid.fields import string_field

    def v(a, b, c):
        raise ValueError('foo')

    @attr.s
    class M:
        f = string_field(is_optional=True, validator=v)

    M(f=None)
    with pytest.raises(ValueError):
        M(f='a')


def test_optional_bool():
    """
    Check that is_optional accepts only True or False
    """
    from attrkid.fields import string_field

    @attr.s
    class Good:
        a = string_field(is_optional=True)
        b = string_field(is_optional=False)

    with pytest.raises(ValueError):

        @attr.s
        class Bad:
            a = string_field(is_optional=None)

    with pytest.raises(ValueError):

        @attr.s
        class Bad:
            a = string_field(is_optional='hello')


def test_object_field():
    from attrkid import to_dict, from_dict
    from attrkid.fields import object_field

    @attr.s
    class X:
        f = attr.ib()

    @attr.s
    class M:
        f = object_field(X)

    m = M(f=X(f=1))
    expected = {'f': {'f': 1}}
    assert expected == to_dict(m)

    loaded = from_dict(M, expected)
    assert m == loaded


def test_object_field_self():
    from attrkid import to_dict, from_dict
    from attrkid.constants import SELF
    from attrkid.fields import object_field
    from attrkid.options import SerdeOptions

    @attr.s
    class M:
        f = object_field(SELF, is_optional=True)

    m = M(f=M(f=None))
    expected = {'f': {}}

    options = SerdeOptions(omit_null_values=True)
    assert expected == to_dict(m, options=options)

    loaded = from_dict(M, expected)
    assert m == loaded


def test_object_field_optional():
    from attrkid import from_dict
    from attrkid.fields import object_field, int_field

    @attr.s
    class X:
        f = int_field()

    @attr.s
    class M:
        f = object_field(X, is_optional=True, default=None)

    assert M(f=None) == from_dict(M, {'f': None})


def test_key_decode_already_key():
    from attrkid import from_dict
    from attrkid.fields import key

    @attr.s
    class X:
        f = attr.ib()

    @attr.s
    class Y:
        k = key(X)

    d = {'k': X(f=1)}
    r = from_dict(Y, d)
    assert Y(k=X(f=1)) == r


def test_linked_object_fields():
    from attrkid.fields import from_dict, object_field

    @attr.s
    class A:
        v = attr.ib()

    @attr.s
    class B:
        a = object_field(A)

    @attr.s
    class C:
        b = object_field(B)

    c = {'b': {'a': {'v': 1}}}

    expected = C(b=B(a=A(v=1)))
    actual = from_dict(C, c)
    assert expected == actual


def test_unique_field():
    from attrkid.fields import string_field
    from attrkid.reflect import is_unique

    @attr.s
    class A:
        v = string_field(unique=True)

    @attr.s
    class B:
        v = string_field()

    a_fields = attr.fields(A)
    b_fields = attr.fields(B)
    assert is_unique(a_fields.v)
    assert not is_unique(b_fields.v)


def test_collection_of_self():
    from attrkid.constants import SELF
    from attrkid.fields import list_field

    @attr.s
    class M:
        ms = list_field(SELF)

    M(ms=[M(ms=[])])
    with pytest.raises(TypeError):
        M(ms=[object()])


def test_int_field():
    from attrkid import from_dict, to_dict
    from attrkid.fields import int_field

    @attr.s
    class M:
        n = int_field()

    x = M(n=5)
    assert x == from_dict(M, to_dict(x))


def test_non_serialisable():
    from attrkid import from_dict, to_dict
    from attrkid.fields import string_field

    @attr.s
    class M:
        a = string_field()
        b = string_field(should_serialise=False)

    m = M(a='a', b='b')
    expected = {'a': 'a'}
    assert expected == to_dict(m)
    m2 = from_dict(M, expected)
    assert 'a' == m2.a
    assert m2.b is None


def test_factory():
    from attrkid.fields import (
        string_field,
        datetime_field,
        int_field,
        decimal_field,
        float_field,
        bool_field,
        bytes_field,
        url_field,
        any_field,
        object_field,
        key,
    )

    dt = datetime.datetime(2018, 1, 1, 12, 0, 0, tzinfo=pytz.utc)

    @attr.s
    class M:
        s = string_field(factory=lambda: 'hello')
        d = datetime_field(factory=lambda: dt)
        i = int_field(factory=lambda: 2)
        dec = decimal_field(factory=lambda: decimal.Decimal('3'))
        f = float_field(factory=lambda: 2.3)
        b = bool_field(factory=lambda: True)
        by = bytes_field(factory=lambda: b'x')
        u = url_field(factory=lambda: 'https://foo.com')
        a = any_field(factory=lambda: 1)
        o = object_field(int, factory=lambda: 2)
        k = key(int, factory=lambda: 3)

    m = M()
    assert 'hello' == m.s
    assert dt == m.d
    assert 2 == m.i
    assert decimal.Decimal('3') == m.dec
    assert 2.3 == m.f
    assert m.b
    assert b'x' == m.by
    assert 'https://foo.com' == m.u
    assert 1 == m.a
    assert 2 == m.o
    assert 3 == m.k


def test_default_from_attr():
    from attrkid import from_dict, to_dict
    from attrkid.fields import string_field, set_field

    @attr.s
    class M:
        f = string_field(default_from_attr='_f')
        s = set_field(str, default_from_attr='_s')

        @property
        def _f(self):
            return 'hello'

        @property
        def _s(self):
            return {'hey'}

    m = M()
    assert 'hello' == m.f
    assert {'hey'} == m.s

    expected = {'f': 'hello', 's': ['hey']}
    assert expected == to_dict(m)

    # default_from_attr only provides defaults
    inp = {'f': 'something', 's': ['different']}
    actual = from_dict(M, inp)
    assert M(f='something', s={'different'}) == actual


def test_to_dict_nested_flags(dt):
    """
    When a sub-model has a datetime, and to_dict is called with
    convert_datetimes=False, make sure that the datetimes are indeed left
    alone. Same for None/null values - `convert_datetimes` and
    `omit_null_values` should be propagated.
    """
    from attrkid import to_dict
    from attrkid.fields import object_field, datetime_field
    from attrkid.constants import SELF
    from attrkid.options import SerdeOptions

    @attr.s
    class M:
        dt = datetime_field()
        sub = object_field(SELF, is_optional=True, default=None)

    m = M(dt=dt, sub=M(dt=dt))
    expected = {'dt': dt, 'sub': {'dt': dt, 'sub': None}}
    options = SerdeOptions(convert_datetimes=False, omit_null_values=False)
    actual = to_dict(m, options=options)
    assert expected == actual


def test_union_field():
    from attrkid import to_dict, from_dict
    from attrkid.fields import (
        bool_field,
        list_field,
        object_field,
    )
    from attrkid.kind import UnionKind

    @attr.s
    class Value:
        value = bool_field()

    @attr.s
    class And:
        items = list_field(Value)

    @attr.s
    class Not:
        item = object_field(Value)

    @attr.s
    class Container:
        item = object_field(UnionKind(('and', And), ('not', Not)))

    c1 = Container(item=And(items=[Value(value=True), Value(value=False)]))
    expected_c1 = {
        'item': {
            'and': {
                'items': [{
                    'value': True
                }, {
                    'value': False
                }],
            }
        }
    }
    actual_c1 = to_dict(c1)
    assert expected_c1 == actual_c1

    c2 = Container(item=Not(item=Value(value=True)))
    expected_c2 = {'item': {'not': {'item': {'value': True}}}}
    actual_c2 = to_dict(c2)
    assert expected_c2 == actual_c2

    assert c1 == from_dict(Container, actual_c1)
    assert c2 == from_dict(Container, actual_c2)


def test_union_field_deferred(mocker):
    from attrkid import from_dict, to_dict
    from attrkid.fields import object_field
    from attrkid.kind import DeferredKind, UnionKind

    import_module = mocker.patch('importlib.import_module')
    import_module.return_value = sys.modules[__name__]

    selector_for = mocker.patch('attrkid.kind.UnionKind.selector_for')
    selector_for.return_value = 'target'

    @attr.s
    class M:
        m = object_field(
            UnionKind(
                ('target', DeferredKind('tests.test_models.TargetModel')), ))

    m = M(m=TargetModel())
    import_module.assert_called_with('tests.test_models')
    as_dict = to_dict(m)
    selector_for.assert_called_with(TargetModel)
    assert m == from_dict(M, as_dict)


def test_only_field():
    from attrkid import from_dict, to_dict
    from attrkid.fields import (
        list_field,
        object_field,
        string_field,
    )

    @attr.s
    class Value:
        value = string_field()

    @attr.s
    class Not:
        item = object_field(Value, is_only_field=True)

    @attr.s
    class And:
        items = list_field(Value, is_only_field=True)

    n = Not(item=Value(value='boo'))
    expected_n = {'value': 'boo'}
    assert expected_n == to_dict(n)
    assert n == from_dict(Not, expected_n)

    a = And(items=[Value(value='hello'), Value(value='world')])
    expected_a = [{'value': 'hello'}, {'value': 'world'}]
    assert expected_a == to_dict(a)
    assert a == from_dict(And, expected_a)


def test_only_union():
    from attrkid import to_dict
    from attrkid.fields import (
        list_field,
        object_field,
        string_field,
    )
    from attrkid.kind import UnionKind

    @attr.s
    class Value:
        value = string_field()

    @attr.s
    class And:
        items = list_field(Value, is_only_field=True)

    @attr.s
    class Not:
        item = object_field(Value, is_only_field=True)

    @attr.s
    class Container:
        expr = object_field(UnionKind(('and', And), ('not', Not)))

    c1 = Container(expr=And(items=[Value('hello'), Value('world')]))
    c2 = Container(expr=Not(item=Value('boo')))

    expected_c1 = {'expr': {'and': [{'value': 'hello'}, {'value': 'world'}]}}
    assert expected_c1 == to_dict(c1)

    expected_c2 = {'expr': {'not': {'value': 'boo'}}}
    assert expected_c2 == to_dict(c2)


def test_any_field():
    """ We should be able to stuff anything into an any_field """
    from attrkid.fields import any_field

    @attr.s
    class M:
        v = any_field()

    M(v='hey')
    M(v=1)
    M(v=object())


def test_list_of_union_kind():
    from attrkid import to_dict
    from attrkid.fields import list_field, string_field
    from attrkid.kind import UnionKind

    @attr.s
    class V1:
        a = string_field()

    @attr.s
    class V2:
        b = string_field()

    @attr.s
    class M:
        v = list_field(UnionKind(('v1', V1), ('v2', V2)), is_only_field=True)

    m = M(v=[V1(a='hello'), V2(b='world')])
    actual = to_dict(m)
    expected = [{'v1': {'a': 'hello'}}, {'v2': {'b': 'world'}}]
    assert expected == actual


def test_field_sorted():
    """ Check that sort_key keeps a list field sorted"""
    from attrkid.fields import list_field

    @attr.s
    class M:
        xs = list_field(int, sort_key=lambda x: x)

    m = M(xs=[3, 2, 1])
    assert [1, 2, 3] == m.xs

    @attr.s
    class N:
        xs = list_field(int, sort_key=lambda x: x, sort_reverse=True)

    n = N(xs=[1, 2, 3])
    assert [3, 2, 1] == n.xs


def test_url_field():
    from attrkid.fields import url_field

    @attr.s
    class M:
        url = url_field()

    with pytest.raises(ValueError):
        M(url='not a url')

    with pytest.raises(ValueError):
        M(url='http://notsecure')

    M(url='https://thisisok')


def test_list_fields_self():
    from attrkid import to_dict, from_dict
    from attrkid.fields import list_field
    from attrkid.constants import SELF

    @attr.s
    class MList:
        as_list = list_field(SELF)

    m1 = MList()
    m2 = MList(as_list=[m1], )
    assert m2 == from_dict(MList, to_dict(m2))


def test_set_field_self():
    from attrkid import from_dict, to_dict
    from attrkid.fields import set_field
    from attrkid.constants import SELF

    @attr.s(hash=True)
    class MSet:
        as_set = set_field(SELF)

    m3 = MSet()
    m4 = MSet(as_set={m3})
    expected_dict = {'as_set': [{'as_set': []}]}
    as_dict = to_dict(m4)
    assert expected_dict == as_dict
    assert m4 == from_dict(MSet, as_dict)


def test_tuple_field_self():
    from attrkid import from_dict, to_dict
    from attrkid.fields import tuple_field
    from attrkid.constants import SELF

    @attr.s
    class MTuple:
        as_tuple = tuple_field(SELF)

    m5 = MTuple()
    m6 = MTuple(as_tuple=(m5, ))
    assert m6 == from_dict(MTuple, to_dict(m6))


def test_tuple_of_union():
    from attrkid import to_dict, from_dict
    from attrkid.fields import string_field, tuple_field
    from attrkid.kind import UnionKind

    @attr.s(hash=True)
    class A:
        f = string_field()

    @attr.s(hash=True)
    class B:
        f = string_field()

    @attr.s(hash=True)
    class C:
        t = tuple_field(UnionKind(
            ('a', A),
            ('b', B),
        ))

    # Check we can round-trip
    a = A(f='a')
    b = B(f='b')
    c = C(t=(a, b))
    as_dict = to_dict(c)
    as_ob = from_dict(C, as_dict)
    assert c == as_ob


def test_key_optional():
    from attrkid.fields import key

    @attr.s
    class M:
        id = key(str)

    @attr.s
    class N:
        id = key(str, is_optional=True)

    M(id='foo')

    with pytest.raises(TypeError):
        M(id=None)
    N(id=None)


def test_datetime_custom_serialisation(dt):
    from attrkid import to_dict
    from attrkid.fields import datetime_field
    from attrkid.options import SerdeOptions

    @attr.s
    class M:
        f = datetime_field()

    m = M(f=dt)
    assert {'f': '2017-11-13T15:12:00.000000Z'} == to_dict(m)
    options = SerdeOptions(datetime_format='%Y')
    assert {'f': '2017'} == to_dict(m, options=options)


def test_decimal_field():
    from attrkid import to_dict, from_dict
    from attrkid.fields import decimal_field

    @attr.s
    class M:
        f = decimal_field(prec=5)

    m = M(f=decimal.Decimal('3.4'))
    as_dict = to_dict(m)
    expected = {'f': '3.4'}
    assert expected == as_dict
    as_ob = from_dict(M, as_dict)
    assert m == as_ob


def test_optional_tuple_field():
    from attrkid import to_dict, from_dict
    from attrkid.fields import tuple_field

    @attr.s
    class X:
        pass

    @attr.s
    class M:
        f = tuple_field(X, is_optional=True, default=None)

    m = M()
    n = M(f=None)
    assert m == n

    as_dict = to_dict(m)
    assert m == from_dict(M, as_dict)

    data = {}
    assert m == from_dict(M, data)
