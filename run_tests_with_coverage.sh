#!/bin/bash

# Run tests with coverage for Zoom Transcript Insights project

# Set up environment
echo "Setting up environment..."
export PYTHONPATH=$(pwd):$PYTHONPATH

# Check if pytest and pytest-cov are installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create necessary directories if they don't exist
mkdir -p tests/data
mkdir -p coverage_reports

# Run the tests with coverage
echo "Running tests with coverage..."
pytest --cov=app --cov-report=term --cov-report=html:coverage_reports tests/

# Check exit status
if [ $? -eq 0 ]; then
    echo "All tests passed!"
    echo "Coverage report generated in coverage_reports directory"
    echo "Open coverage_reports/index.html in a browser to view the detailed report"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi 