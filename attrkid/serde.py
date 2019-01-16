import attr

from .constants import (
    COLLECTION_TYPES,
    DESERIALISE,
    MISSING,
    SERIALISE,
)
from .exceptions import ValidationError
from .kind import UnionKind
from .options import SerdeOptions
from .reflect import field_subtype, field_type, is_only_field, should_serialise
from .validators import validate

# Just create our default options once as it's used 99% of the time
# (This is safe as SerdeOptions is immutable)
_DEFAULT_OPTIONS = SerdeOptions()


def from_dict(cls, data, *, defaults=None):
    """
    Deserialize `data` into a `cls` instance. If `data` is not an attrs class,
    we assume there's nothing to do.

    Args:
        cls: The class to instantiate
        data: Data to parse
        defaults: Any defaults from missing data

    Returns:

    """
    if not attr.has(cls):
        return data

    kw = {}
    if defaults is None:
        defaults = {}

    for f in attr.fields(cls):
        # If this field is the only field, then we don't have to extract
        # a value out of the data dict - the whole value *is* the data dict.
        value = MISSING
        if is_only_field(f):
            raw = data
        else:
            raw = data.get(f.name, MISSING)

            # If we pull a value from defaults and it's not an attrs class,
            # we'll treat it as a fully-fledged value note requiring
            # deserialisation.
            if raw is MISSING:
                default = defaults.get(f.name, MISSING)
                if default is not MISSING:
                    if attr.has(default):
                        value = default
                    else:
                        raw = default

        if raw is MISSING and value is MISSING:
            if f.default is not attr.NOTHING:
                if isinstance(f.default, attr.Factory):
                    value = f.default.factory()
                else:
                    value = f.default
            else:
                value = None

        if value is MISSING:
            try:
                value = _do_deserialise(cls, f, raw)
            except Exception as exc:
                raise ValidationError(
                    errors=[{
                        'field': f,
                        'exc': exc
                    }], exc=exc) from exc
        kw[f.name] = value

    try:
        return cls(**kw)
    except Exception as exc:
        # If something bad happened, try to run the validators again
        # individually as a best-effort to figure out what went wrong. This
        # isn't perfect, because we don't have an instance to play with.
        errors = validate(cls, kw)
        if errors:
            raise ValidationError(errors=errors, exc=exc) from exc
        raise


def to_dict(instance, *, options: SerdeOptions = None):
    """
    Serialize `instance` into a dict.
    Args:
        instance: The instance to serialise
        options: A SerdeOptions instance to control serialisation
    Returns:
        A dict (or list, oops, if it's a top-level collection type!)
        representing the model
    """
    if options is None:
        options = _DEFAULT_OPTIONS

    # We may get passed a top-level collection. Handle that directly here by
    # serialising elements as a list - obviously we don't have a field at
    # this point to pull out a custom serialiser.
    if isinstance(instance, COLLECTION_TYPES):
        return [to_dict(
            each,
            options=options,
        ) for each in instance]

    if not attr.has(instance):
        return instance

    if options.union is not None:
        # If we're serialising a union, we need to make sure we serialise the
        # correct top-level tag.
        data = {}
        selector = options.union.selector_for(type(instance))

        rv = {selector: data}
    else:
        rv = {}
        data = rv
        selector = None

    # Note we've arranged things so the code always updates the dict
    # pointed to by `data`. This might be a top-level dict, or it might be
    # the data dict wrapped for the benefit of the UnionField.
    for field in attr.fields(type(instance)):
        if not should_serialise(field):
            continue
        value = getattr(instance, field.name)

        # Figure out if we're processing a field with a UnionKind
        mu = _maybe_union(field)
        if mu != options.union:
            options = attr.evolve(options, union=mu)

        # If this is the only field, then we skip serialisation of this field
        # and directly return the serialised value. Note that if we're wrapping
        # the value in a container (ie. we have a valid selector) then we
        # put the value in the rv dict rather than returning it directly.
        if is_only_field(field):
            only_field_value = to_dict(value, options=options)
            if selector:
                rv[selector] = only_field_value
                return rv
            else:
                return only_field_value

        if options.omit_null_values and value is None:
            continue
        value = _do_serialise(
            field,
            value,
            options=options,
        )
        data[field.name] = value
    return rv


def _maybe_union(field):
    # Figure out if we're processing in the context of a UnionKind. If we
    # are, then we need to pass it down to the next layers as it will
    # eventually need to be serialised slightly differently.
    type_, = field_type(field, default=(None, ), unwrap=False)
    subtype, = field_subtype(field, default=(None, ), unwrap=False)
    union = None
    for t in (type_, subtype):
        if isinstance(t, UnionKind):
            union = t
            break
    return union


def _do_deserialise(owning_cls, field, value):
    """
    If the current field has a deserialise function, call it. We expect this to
    be tolerant of None and of values that are already of the right type.
    """
    deserialise = field.metadata.get(DESERIALISE)
    if deserialise is not None:
        value = deserialise(owning_cls, field, value)
    return value


def _do_serialise(field, value, *, options: SerdeOptions):
    serialiser = field.metadata.get(SERIALISE)
    if serialiser is not None:
        value = serialiser(
            field,
            value,
            options=options,
        )
    elif attr.has(value):
        value = to_dict(value, options=options)
    return value
