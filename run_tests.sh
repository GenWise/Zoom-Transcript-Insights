#!/bin/bash

# Run tests for Zoom Transcript Insights project

# Set up environment
echo "Setting up environment..."
export PYTHONPATH=$(pwd):$PYTHONPATH

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing..."
    pip install pytest
fi

# Create necessary directories if they don't exist
mkdir -p tests/data

# Run the tests
echo "Running tests..."
python tests/run_tests.py

# Check exit status
if [ $? -eq 0 ]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed."
    exit 1
fi 