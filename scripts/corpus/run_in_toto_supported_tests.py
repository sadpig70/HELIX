#!/usr/bin/env python3
"""Run in-toto tests supported on Windows without Developer Mode.

The three excluded tests require OS symlink creation and fail with WinError 1314
when Windows Developer Mode is disabled. They are environmental capability tests,
not silently treated as passing.
"""

import json
import os
import sys
import unittest


EXCLUDED = {
    "tests.test_runlib.TestRecordArtifactsAsDict.test_record_follow_symlinked_directories",
    "tests.test_runlib.TestRecordArtifactsAsDict.test_record_symlinked_files",
    "tests.test_runlib.TestRecordArtifactsAsDict.test_record_without_dead_symlinks",
}


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    project_root = os.getcwd()
    sys.path = [path for path in sys.path
                if os.path.abspath(path or project_root) != project_root]
    sys.path.insert(0, project_root)
    discovered = unittest.defaultTestLoader.discover(
        start_dir=os.path.join(project_root, "tests"), top_level_dir=project_root)
    tests = list(flatten(discovered))
    selected = [test for test in tests if test.id() not in EXCLUDED]
    observed_exclusions = sorted(test.id() for test in tests if test.id() in EXCLUDED)
    if observed_exclusions != sorted(EXCLUDED):
        print(json.dumps({"error": "exclusion set drift",
                          "expected": sorted(EXCLUDED),
                          "observed": observed_exclusions}, indent=2), file=sys.stderr)
        return 4
    print(json.dumps({
        "schema": "helix-supported-test-scope/1.0",
        "platform": os.name,
        "selected": len(selected),
        "excluded": observed_exclusions,
        "reason": "Windows Developer Mode symlink privilege unavailable",
    }, indent=2))
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
