import os
import glob
from pathlib import Path
from typing import List, Optional

class TestDiscovery:
    def __init__(self, directories: Optional[List[str]] = None, tests: Optional[List[str]] = None):
        """
        Initialize the TestDiscovery class.

        Args:
            directories: List of directories to search for tests. If None, defaults to current directory.
            tests: List of specific test names to look for.
        """
        self.directories = [Path(d).resolve() for d in directories] if directories else [Path.cwd()]
        self.tests = tests
        self.found_tests = []

    def discover(self) -> List[Path]:
        """
        Discover unit tests in the specified directories.

        Returns:
            List of paths to the found unit test files.
        """
        self.found_tests = []
        for directory in self.directories:
            self._find_tests_in_directory(directory)
        return self.found_tests

    def _find_tests_in_directory(self, directory: Path):
        """
        Recursively find tests in a directory.
        """
        if not directory.exists():
            print(f"Warning: Directory {directory} does not exist.")
            return

        # If specific tests are requested
        if self.tests:
            for test in self.tests:
                test_path = directory / test
                if test_path.exists():
                    self.found_tests.append(test_path)
                else:
                    # Check if it exists with _unit_test.sv suffix if not provided
                    if not test.endswith("_unit_test.sv"):
                        test_path_suffix = directory / f"{test}_unit_test.sv"
                        if test_path_suffix.exists():
                            self.found_tests.append(test_path_suffix)
                            continue
                    
                    # If we are here, we haven't found the test in this directory.
                    # However, we shouldn't error out immediately because it might be in a subdirectory
                    # or another directory in the list.
                    # But the original Perl script seems to error if a specified test is not found in the dir.
                    # Let's stick to finding all matching files recursively if no specific test is given,
                    # or checking specific paths if tests are given.
                    pass
        else:
            # Find all *_unit_test.sv files
            # Using rglob for recursive search
            for test_file in directory.rglob("*_unit_test.sv"):
                self.found_tests.append(test_file)

    def get_test_suites(self):
        """
        Group found tests by directory to form test suites.
        Returns a dictionary where keys are directory paths and values are lists of test files.
        """
        suites = {}
        for test_file in self.found_tests:
            parent_dir = test_file.parent
            if parent_dir not in suites:
                suites[parent_dir] = []
            suites[parent_dir].append(test_file)
        return suites
