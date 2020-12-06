from unittest import TestSuite

from tests.test_extract_info import TestExtractInfo
from tests.test_extract_subs import TestExtractSubs
from tests.test_storage import TestStorage
from tests.test_util import TestUtils

test_cases = (TestExtractInfo, TestExtractSubs, TestStorage, TestUtils)


def load_tests(loader, tests, pattern):
    suite = TestSuite()
    for test_class in test_cases:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite
