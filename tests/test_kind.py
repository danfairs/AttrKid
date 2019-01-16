import attr


@attr.s
class A:
    pass


@attr.s
class B:
    pass


def test_wrap_kind_multiple():
    from attrkid.kind import DeferredKind, ImmediateKind, wrap_kind

    @wrap_kind()
    def check(kind):
        assert (DeferredKind('tests.test_utils.A'), ImmediateKind(B)) == kind

    kinds = (DeferredKind('tests.test_utils.A'), B)
    check(kinds)
