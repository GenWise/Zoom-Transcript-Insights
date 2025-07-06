#!/usr/bin/env python3
"""
Script to run all tests for the Zoom Transcript Insights project.
"""

import unittest
import pytest
import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_unittest_tests():
    """Run tests using unittest framework."""
    print("Running unittest tests...")
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    return result.wasSuccessful()

def run_pytest_tests():
    """Run tests using pytest framework."""
    print("Running pytest tests...")
    result = pytest.main(['-xvs', 'tests'])
    return result == 0

if __name__ == "__main__":
    # Run tests with both frameworks
    unittest_success = run_unittest_tests()
    pytest_success = run_pytest_tests()
    
    # Exit with appropriate status code
    if unittest_success and pytest_success:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1) 