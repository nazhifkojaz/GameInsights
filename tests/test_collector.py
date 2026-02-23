"""Backward compatibility module for split collector tests.

This module re-exports all test classes from the split test files to maintain
backward compatibility with any external tooling that expects tests in this file.
"""

# Import from split test modules
from tests.collector.test_dataframe import TestCollectorDataFrame
from tests.collector.test_error_classification import (
    TestCollectorErrorClassification,
    TestRaiseForFetchFailure,
    TestRaiseOnErrorParameter,
)
from tests.collector.test_error_handling import (
    TestCollectorErrorHandling,
    TestCollectorFailureReporting,
)
from tests.collector.test_fetching import TestCollectorFetching
from tests.collector.test_metrics import TestCollectorMetrics
from tests.collector.test_multi_appid import TestMultiAppidScenarios
from tests.collector.test_properties import TestCollectorConfiguration, TestCollectorProperties
from tests.collector.test_user_data import TestGetUserData

# Re-export for backward compatibility
TestCollector = TestCollectorFetching

__all__ = [
    "TestCollector",
    "TestCollectorFetching",
    "TestCollectorDataFrame",
    "TestCollectorErrorHandling",
    "TestCollectorFailureReporting",
    "TestCollectorErrorClassification",
    "TestRaiseForFetchFailure",
    "TestRaiseOnErrorParameter",
    "TestCollectorMetrics",
    "TestMultiAppidScenarios",
    "TestCollectorProperties",
    "TestCollectorConfiguration",
    "TestGetUserData",
]
