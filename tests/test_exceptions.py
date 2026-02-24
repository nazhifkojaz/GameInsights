"""Backward compatibility module for split exception tests.

This module re-exports all test classes from the split test files to maintain
backward compatibility with any external tooling that expects tests in this file.
"""

# Import from split test modules
from tests.collector import test_error_classification as _collector_error
from tests.model import test_model_exceptions as _model_exceptions


# Re-export as lightweight subclasses to avoid mutating original classes
class TestExceptionHierarchy(_model_exceptions.TestExceptionHierarchy):
    __test__ = False


class TestDependencyNotInstalledError(_model_exceptions.TestDependencyNotInstalledError):
    __test__ = False


class TestCollectorErrorClassification(_collector_error.TestCollectorErrorClassification):
    __test__ = False


class TestRaiseForFetchFailure(_collector_error.TestRaiseForFetchFailure):
    __test__ = False


class TestRaiseOnErrorParameter(_collector_error.TestRaiseOnErrorParameter):
    __test__ = False


__all__ = [
    "TestExceptionHierarchy",
    "TestCollectorErrorClassification",
    "TestRaiseForFetchFailure",
    "TestRaiseOnErrorParameter",
    "TestDependencyNotInstalledError",
]
