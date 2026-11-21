"""One entry point for every requested workbook test and independent unit tests."""
from pathlib import Path
import unittest

import pandas as pd

import run_tests
import run_advanced_tests


def main():
    run_tests.main()
    run_advanced_tests.main()
    here = Path(__file__).resolve().parent
    old = pd.read_csv(run_tests.OUTPUT / "validation_summary.csv", dtype={"test": str})
    new = pd.read_csv(run_advanced_tests.OUTPUT / "advanced_validation_summary.csv", dtype={"test": str})
    combined = pd.concat([old, new], ignore_index=True)
    assert len(combined) == 50 and combined.test.nunique() == 50
    assert (combined.status == "PASS").all()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_*risk*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    combined.to_csv(run_tests.OUTPUT / "all_validation_summary.csv", index=False)
    print(f"\n50/50 workbook tests passed; {result.testsRun} independent tests passed.")


if __name__ == "__main__":
    main()
