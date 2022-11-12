from contextlib import contextmanager

from hypothesis.extra.django import TestCase as HypTestCase


class TestBase(HypTestCase):
    @contextmanager
    def assertNoException(self, exception_type):
        try:
            yield
        except exception_type:
            self.fail("%s exception type raised" % exception_type)
