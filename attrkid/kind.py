import abc
import importlib
from typing import Union

import attr
import functools


class ProxyKind(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self) -> tuple:
        """ Return a tuple of concrete types """

    def unwrap(self):
        r = ()
        for t in self.get():
            if isinstance(t, ProxyKind):
                r += t.unwrap()
            else:
                r += t,
        return r


# Note that we don't specify slots=True on these, as this breaks issubclass.
# It looks like attrs would need to add a __weakref__ slot for this to work,
# as issubclass uses weakrefs in its caching implementation
@attr.s(frozen=True)
class DeferredKind(ProxyKind):
    kind = attr.ib(validator=attr.validators.instance_of(str))

    def get(self):
        mod_name, class_name = self.kind.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        return getattr(mod, class_name),


@attr.s(frozen=True)
class ImmediateKind(ProxyKind):
    # This will be a type, or SELF
    kind = attr.ib()

    def get(self):
        return self.kind,


@attr.s(init=False)
class UnionKind(ProxyKind):
    # This should be a tuple of name/type pairs
    kinds = attr.ib(validator=attr.validators.instance_of(tuple))

    def __init__(self, *kinds):
        self.kinds = kinds

    def get(self):
        return tuple([kind for name, kind in self.kinds])

    def _concrete_kinds(self):
        for name, k in self.kinds:
            while isinstance(k, ProxyKind):
                k, = k.get()
            yield name, k

    def selector_for(self, kind):
        for name, k in self._concrete_kinds():
            if k == kind:
                return name
        raise ValueError(kind)

    def kind_for(self, selector):
        for name, k in self._concrete_kinds():
            if name == selector:
                return k
        raise ValueError(selector)


PROXY_KINDS = (DeferredKind, ImmediateKind, UnionKind)


def wrap_one_kind(k) -> Union[DeferredKind, ImmediateKind]:
    if not isinstance(k, PROXY_KINDS) and k is not None:
        k = ImmediateKind(k)
    return k


def wrap_kind(*, kwarg_names=()):
    """
    Wrap the first kind argument of the decorated function (and any kwargs
    specified in `kwargs_names` with DeferredKind and ImmediateKind wrappers
    as appropriate.

    Note that we always pass a tuple back as the wrapped kind, regardless of
    whether we were passed a single type or a tuple of types. Our own
    type validators expect tuples.
    Args:
        kwarg_names:

    Returns:

    """

    def _wrap(k):
        if not isinstance(k, tuple):
            k = k,
        return tuple([wrap_one_kind(k1) for k1 in k if k1])

    def _func(func):

        @functools.wraps(func)
        def _wrapped(kind, *args, **kwargs):
            for name in kwarg_names:
                if name in kwargs:
                    kwargs[name] = _wrap(kwargs[name])

            # We always wrap the `kind` argument
            kind = _wrap(kind)
            return func(kind, *args, **kwargs)

        return _wrapped

    return _func


def union_parts(union: UnionKind, value: dict):
    """
    Given a UnionKind instance and the structure used to deserialise it,
    return a 2-tuple of the concrete kind that should be used to deserialise
    the concrete data, and the data to be used. The incoming `value` should be
    of the form:

    {
        'selector': {
            'id': '1234',
            'title': 'hello'
        }
    }

    This example might return a 2-tuple like:

        (Selector, {'id': '1234', 'title': 'hello'})

    Args:
        union: the UnionKind to process
        value: The data with type selector

    Returns:
        a 2-tuple of (type, data)

    """
    selector, sub_value = list(value.items())[0]
    final_kind = union.kind_for(selector)
    value = sub_value
    return final_kind, value
