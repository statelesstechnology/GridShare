import unittest
import sys
import os

if __name__ == '__main__':
    # Add the backend directory to sys.path to allow imports of app, db_utils, etc.
    # Assumes this script is in emds/backend/
    # and tests are in emds/backend/tests/
    # and modules like app.py, db_utils.py are in emds/backend/

    # For app.py, db_utils.py etc. to be importable by test files:
    # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # For simulation_engine modules to be importable by test files:
    # sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simulation_engine'))


    # More robust way: add the project root (emds) to path if backend is a package
    # This assumes 'emds' is the top-level project folder.
    # And that you run `python backend/run_tests.py` from within `emds/`
    # or that `emds` is in PYTHONPATH.
    # If `emds/backend` is intended to be a package, then imports within tests
    # should be like `from backend.app import app` etc. after adding `emds` to path.

    # Simpler approach if run_tests.py is in `emds/backend/` and tests are in `emds/backend/tests/`:
    # The tests themselves might need to adjust sys.path if they are directly run.
    # unittest.discover should handle imports correctly if the structure is standard.
    # Let's assume standard structure where `emds/backend` is on PYTHONPATH or tests adjust path.

    loader = unittest.TestLoader()
    # Discover tests in the 'tests' subdirectory relative to this script's location
    # (emds/backend/tests)
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(test_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2) # Increased verbosity
    result = runner.run(suite)

    if result.wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
