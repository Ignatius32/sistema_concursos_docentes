"""
Run the placeholder resolver test suite.
"""
import subprocess
import os
import sys

def run_tests():
    """Run the placeholder resolver test suite."""
    print("Running placeholder resolver test suite...")
    
    # Get the tests directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(root_dir, 'tests')
    
    # Define the test files to run
    test_files = [
        'test_placeholder_resolver_simple.py',
        'test_placeholder_resolver_mocked.py',
        'test_integration_document_generator.py',
        'test_integration_notifications.py'
    ]
    
    # Build the command
    test_paths = [os.path.join(tests_dir, file) for file in test_files]
    command = [sys.executable, '-m', 'pytest'] + test_paths + ['-v']
    
    # Run the tests
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Print the output
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"Tests failed with return code {result.returncode}")
        print(result.stderr)
        return False
    
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
