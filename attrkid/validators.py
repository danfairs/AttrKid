import attr

from .constants import SELF, COLLECTION_TYPES
from .kind import wrap_kind, ProxyKind


def validate(kind, data):
    errors = []
    for field in attr.fields(kind):
        value = data.get(field.name)
        if field.validator is not None:
            try:
                field.validator(None, field, value)
            except Exception as exc:
                errors.append({'field': field, 'exc': exc})
    return errors


@wrap_kind()
def collection_of(kind):
    """
    attrs validator that checks the value is a collection of `kind`.
    Args:
        kind: The class to check for

    Raises a `TypeError` if validation fails.

    """
    return _CollectionOfValidator(kind)


def one_of(values):
    """
    Return a validator which checks that the value is in the given set of
    values.
    Args:
        values:

    Returns:

    """
    value_set = set(values)
    try:
        values_str = ', '.join([v for v in values])
    except TypeError:
        values_str = '(cannot convert to string)'

    def _one_of(inst, attr, value):
        if value not in value_set:
            raise ValueError(f'{value} is not in the set of allowed values '
                             f'{values_str} for field {attr}')

    return _one_of


def all_of(*validators):
    """
    Simply invokes all the given validators
    Args:
        validators:

    Returns:

    """

    def _all_of(inst, attr, value):
        for validator in validators:
            validator(inst, attr, value)

    return _all_of


@wrap_kind()
def instance_of(kind):
    return _DeferredInstanceOfValidator(kind)


@attr.s(repr=False, slots=True, hash=True)
class _DeferredInstanceOfValidator:
    type = attr.ib(validator=attr.validators.instance_of(tuple))

    def __call__(self, inst, attr, value):
        typ = _transform(self.type, instance_type=type(inst))

        if not isinstance(value, typ):
            raise TypeError(
                "'{name}' must be {type!r} (got {value!r} that is a "
                "{actual!r}).".format(
                    name=attr.name,
                    type=self.type,
                    actual=value.__class__,
                    value=value),
                attr,
                self.type,
                value,
            )

    def __repr__(self):
        return (
            "<instance_of validator for type {type!r}>".format(type=self.type))


def _transform(typ, *, instance_type) -> tuple:
    r = ()
    for t in typ:
        if isinstance(t, ProxyKind):
            r += _transform(t.get(), instance_type=instance_type)
        elif t is SELF:
            r += instance_type,
        else:
            r += t,
    return r


@attr.s(repr=False, slots=True)
class _CollectionOfValidator:
    type = attr.ib(validator=attr.validators.instance_of(tuple))

    def __call__(self, inst, attr, value):
        """
        We use a callable class to be able to change the ``__repr__``.
        """
        if not isinstance(value, COLLECTION_TYPES):
            raise TypeError(
                f'`{attr.name}` must be a collection type, it was `{value}`')

        typ = _transform(self.type, instance_type=type(inst))
        ok = [isinstance(item, typ) for item in value]
        if not all(ok):
            errors = []
            for i, v in enumerate(ok):
                if not v:
                    as_list = list(value)
                    errors.append(
                        f'`{as_list[i]}` is not of type `{self.type!r}` at '
                        f'index {i} (attribute `{attr.name}` of `{type(inst)})`'
                    )
            raise TypeError(''.join(errors))

    def __repr__(self):
        return ("<collection_of validator for type {type!r}>"
                .format(type=self.type))
