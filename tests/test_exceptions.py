"""Backward compatibility module for split exception tests.

This module re-exports all test classes from the split test files to maintain
backward compatibility with any external tooling that expects tests in this file.
"""

# Import from split test modules
from tests.collector import test_error_classification as _collector_error
from tests.model import test_model_exceptions as _model_exceptions

# Re-export for backward compatibility
TestExceptionHierarchy = _model_exceptions.TestExceptionHierarchy
TestDependencyNotInstalledError = _model_exceptions.TestDependencyNotInstalledError
TestCollectorErrorClassification = _collector_error.TestCollectorErrorClassification
TestRaiseForFetchFailure = _collector_error.TestRaiseForFetchFailure
TestRaiseOnErrorParameter = _collector_error.TestRaiseOnErrorParameter

__all__ = [
    "TestExceptionHierarchy",
    "TestCollectorErrorClassification",
    "TestRaiseForFetchFailure",
    "TestRaiseOnErrorParameter",
    "TestDependencyNotInstalledError",
]
