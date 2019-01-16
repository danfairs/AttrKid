from typing import Union, Any

import attr

from .constants import (
    IS_DEFAULT_FROM_ATTR,
    IS_KEY,
    IS_ONLY_FIELD,
    IS_PK,
    IS_UNIQUE,
    MISSING,
    SHOULD_SERIALISE,
    SUBTYPE,
    TYPE,
)


def primary_key_for(kind):
    for f in attr.fields(kind):
        if is_primary_key(f):
            return f
    raise ValueError(kind)


def primary_key_value_for(instance):
    pk_field = primary_key_for(type(instance))
    return getattr(instance, pk_field.name)


def is_key(f):
    return IS_KEY in f.metadata


def is_primary_key(f):
    return f.metadata.get(IS_PK, False)


def is_unique(f):
    return f.metadata.get(IS_UNIQUE, False)


def is_default_from_attr(f):
    return f.metadata.get(IS_DEFAULT_FROM_ATTR, False)


def should_serialise(f):
    return f.metadata.get(SHOULD_SERIALISE, True)


def is_only_field(f):
    return f.metadata.get(IS_ONLY_FIELD, False)


def _field_type(f, metadata_field, default, *, unwrap: bool):
    proxy_tuple = f.metadata.get(metadata_field, (None, ))
    if proxy_tuple:
        proxy, = proxy_tuple
        if proxy:
            if unwrap:
                return proxy.get()
            else:
                return proxy,

    if default is not MISSING:
        return default

    raise TypeError('{} does not have type information'.format(f.name))


def field_type(f, default=MISSING, *, unwrap=True) -> Union[tuple, Any]:
    """
    Return a tuple of types for a field, or `default` if there is no type
    information and a default is specified.

    All fields will return a single-element tuple, unless it was configured
    with a `UnionKind`, in which case all types in the union will be returned.

    If `unwrap` is True, then the tuple of types will be specified. If it is
    False, then the tuple of type *proxies* will be returned - these could
    be `UnionKind`, `ImmediateKind`, or `DeferredKind` instances.

    Args:
        f: The field
        default: Default to return if no type info is found
        unwrap: Whether the type proxies should be unwrapped (default True)

    Returns:
        Tuple of types
    """
    return _field_type(f, TYPE, default, unwrap=unwrap)


def field_subtype(f, default=MISSING, *, unwrap=True):
    """
    When a field is a container type, the subtype is the type of the
    contained item. Other commentary is the same as for `field_type`.
    """
    return _field_type(f, SUBTYPE, default, unwrap=unwrap)
