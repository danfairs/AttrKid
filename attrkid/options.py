import attr
from attr.validators import instance_of, optional

from .kind import UnionKind

DEFAULT_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


@attr.s(frozen=True, slots=True, hash=True)
class SerdeOptions:
    """
    Settings for serialisation and deserialisation
    """
    # Use attr.ib directly here to avoid a circular import with .fields.

    # When serialising, should the output contain whose values are null, or
    # omit them entirely?
    omit_null_values = attr.ib(validator=instance_of(bool), default=True)

    # Should datetimes be serialised to strings?
    convert_datetimes = attr.ib(validator=instance_of(bool), default=True)

    # If datetimes are being serialised, what format should be used?
    datetime_format = attr.ib(
        validator=instance_of(str), default=DEFAULT_DATETIME_FORMAT)

    # The UnionKind in force, if any
    union = attr.ib(validator=optional(instance_of(UnionKind)), default=None)
