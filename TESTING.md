# Testing Strategy for Zoom Transcript Insights

This document outlines the testing strategy for the Zoom Transcript Insights application.

## Overview

The application is tested using a combination of unit tests and integration tests. The tests are written using both the `unittest` framework and `pytest`.

## Test Structure

- **Unit Tests**: Test individual components in isolation
  - `test_vtt_parser.py`: Tests for the VTT parser module
  - `test_analysis.py`: Tests for the analysis service
  - `test_config.py`: Tests for the configuration module
  - `test_mock_data.py`: Tests for generating mock data

- **Integration Tests**: Test the interaction between components
  - `test_integration.py`: Tests for the end-to-end workflow

## Running Tests

### Basic Test Execution

To run all tests:

```bash
./run_tests.sh
```

This script will:
1. Set up the Python environment
2. Install required dependencies if needed
3. Run tests using both `unittest` and `pytest`

### Coverage Testing

To run tests with coverage reporting:

```bash
./run_tests_with_coverage.sh
```

This will generate a coverage report in the `coverage_reports` directory. Open `coverage_reports/index.html` in a browser to view the detailed report.

## Test Data

The tests use a combination of:
- Temporary files created during test execution
- Sample data files in the `tests/data` directory

## Mocking Strategy

External dependencies are mocked to avoid making actual API calls during testing:

- **Claude API**: Mocked to return predefined responses
- **Google Drive API**: Mocked to simulate file operations
- **Zoom API**: Mocked to simulate webhook events and API responses

## Async Testing

For testing asynchronous functions, we use:
- `pytest-asyncio` for proper handling of coroutines
- The `@pytest.mark.asyncio` decorator for async test functions

## Adding New Tests

When adding new tests:

1. For unit tests, add them to the appropriate test file or create a new one
2. For integration tests, add them to `test_integration.py`
3. Follow the existing patterns for setting up test fixtures and mocks
4. Run the tests to ensure they pass

## Continuous Integration

The tests are designed to be run in a CI/CD pipeline. They do not require any external services to be running.

## Code Coverage Goals

- **Core Services**: Aim for >90% coverage
- **API Routes**: Aim for >80% coverage
- **Overall**: Aim for >70% coverage

Current coverage: 42% (as of initial implementation) 