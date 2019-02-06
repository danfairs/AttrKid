AttrKid
=======

![build status](https://travis-ci.org/danfairs/AttrKid.svg?branch=master)

Welcome to AttrKid!

AttrKid allows you to build nested, typed `attrs` classes, with support for serialising deserialising to dictionaries and lists, validating on the way. From there it's a simple hop to JSON.

It's built on the excellent [attrs](https://github.com/python-attrs/attrs) library.

Here's what it looks like:

```
import attr
from attrkid import from_dict, to_dict
from attrkid.fields import object_field, string_field

@attr.s
class Address:
    line_1 = string_field()
    line_2 = string_field()
    postcode = string_field()


@attr.s
class Person:
    name = string_field()
    home = object_field(Address, is_optional=True)
    work = object_field(Address, is_optional=True)

>>> address_1 = Address(line_1='10 Some Street', line_2='Some Town', postcode='AB12 3AB')
>>> person = Person(name='Chris Surname', home=address_1, work=None)
>>> person
Person(name='Chris Surname', home=Address(line_1='10 Some Street', line_2='Some Town', postcode='AB12 3AB'), work=None)
>>> as_dict = to_dict(person)
>>> as_dict
{'name': 'Chris Surname',
 'home': {'line_1': '10 Some Street',
  'line_2': 'Some Town',
  'postcode': 'AB12 3AB'}}
>>> another_person = from_dict(Person, as_dict)
>>> another_person
Person(name='Chris Surname', home=Address(line_1='10 Some Street', line_2='Some Town', postcode='AB12 3AB'), work=None)
>>> another_person == person
True
```

There are lots of fields available out-of-the-box:
- Strings (`string_field`)
- Collections (`list_field`, `tuple_field`, `set_field`)
- Datetimes (`datetime_field`)
- Numbers (`int_field`, `float_field`, `decimal_field`)
- Booleans (`bool_field`)
- Bytes (`bytes_field`)

It can also handle unions of types, round-tripped through dictionaries:

```
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

>>> c1 = Container(item=And(items=[Value(value=True), Value(value=False)]))
>>> c2 = Container(item=Not(item=Value(value=True)))
>>> to_dict(c1)
{'item': {'and': {'items': [{'value': True}, {'value': False}]}}}
>>> to_dict(c2)
{'item': {'not': {'item': {'value': True}}}}
```

In that previous example, you might notice that the `items` element in the serialised dict is a little superflous, since it's the only field. You can tell AttrKid to use a more compact serialisation in that case:

```
@attr.s
class Value:
    value = string_field()

@attr.s
class Not:
    item = object_field(Value, is_only_field=True)

@attr.s
class And:
    items = list_field(Value, is_only_field=True)

>>> n = Not(item=Value(value='boo'))
>>> to_dict(n)
{'value': 'boo'}
>>> a = And(items=[Value(value='hello'), Value(value='world')])
>>> to_dict(a)
[{'value': 'hello'}, {'value': 'world'}]
```

You can also specify class names as strings, to help you out of dependency knots:

```
from attrkid.kinds import DeferredKind

@attr.s
class Person:
    name = string_field()

    # Oops, myproj.models imports from this file, so we can't import it directly
    home = object_field(DeferredKind('myproj.models.Address'), is_optional=True)
    work = object_field(DeferredKind('myproj.models.Address'), is_optional=True)

```


AttrKid was spun out of the [Poli](https://polihq.com) codebase. 