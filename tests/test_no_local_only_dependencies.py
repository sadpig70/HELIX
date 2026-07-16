import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "tests"

LOCAL_ONLY_ROOT_JOIN = re.compile(
    r"""(?:os\.path\.join\(\s*ROOT\s*,\s*["'](?:_workspace|\.helix|\.aox|\.sdx|\.tcx|\.idx|\.cix|\.evx|\.recreate)["'])"""
)
ABSOLUTE_DRIVE_PATH = re.compile(r"""["'][A-Za-z]:[\\/][^"']*["']""")


class NoLocalOnlyDependencyTests(unittest.TestCase):
    def test_tests_do_not_read_or_write_ignored_workspace_roots(self):
        offenders = []
        for path in sorted(TEST_ROOT.glob("test_*.py")):
            if path.name == pathlib.Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            for match in LOCAL_ONLY_ROOT_JOIN.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")

        self.assertEqual([], offenders)

    def test_tests_do_not_embed_machine_absolute_paths(self):
        offenders = []
        for path in sorted(TEST_ROOT.glob("test_*.py")):
            if path.name == pathlib.Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            for match in ABSOLUTE_DRIVE_PATH.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")

        self.assertEqual([], offenders)
