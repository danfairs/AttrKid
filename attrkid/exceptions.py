# TODO(dan): Sort out how this displays in tracebacks, it's terrible
class ValidationError(Exception):

    def __init__(self, errors, exc=None):
        self.errors = errors
        self.exc = exc
        self._str = str(exc) if exc is not None else '' + ', '.join(
            [str(e) for e in errors])

    def __str__(self):
        return self._str
