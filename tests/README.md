# Tests for Zoom Transcript Insights

This directory contains tests for the Zoom Transcript Insights application.

## Test Structure

- `test_vtt_parser.py`: Tests for the VTT parser module
- `test_analysis.py`: Tests for the analysis service
- `test_integration.py`: Integration tests for the end-to-end workflow
- `test_config.py`: Tests for the configuration module
- `test_mock_data.py`: Tests for generating mock data

## Running Tests

You can run the tests using the provided script:

```bash
./run_tests.sh
```

Or manually:

```bash
# Using unittest
python -m unittest discover tests

# Using pytest
pytest tests
```

## Test Data

The `data` directory contains sample files used for testing:

- `sample.vtt`: A sample VTT transcript file

## Adding New Tests

When adding new tests:

1. Create a new test file with the naming pattern `test_*.py`
2. Use either the `unittest` framework or `pytest`
3. Add fixtures to `conftest.py` if using pytest
4. Add any necessary test data to the `data` directory

## Mock Strategy

For external dependencies like Claude API and Google Drive API, we use mocks to avoid making actual API calls during testing. See `test_analysis.py` for examples of how to mock these dependencies. 