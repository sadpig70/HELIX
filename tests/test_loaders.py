import json
import os
import tempfile
import unittest

import tests._path  # noqa: F401
from engines.loaders import load_exploit_state


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f)


class TestExploitLoader(unittest.TestCase):
    def test_loads_candidates_from_latest_run(self):
        with tempfile.TemporaryDirectory() as d:
            write_json(os.path.join(d, ".recreate", "registry.json"),
                       {"schema_version": "1.0", "generated_projects": {}})
            write_json(os.path.join(d, ".recreate", "latest.json"),
                       {"latest_run_path": ".recreate/runs/001-demo"})
            write_json(os.path.join(d, ".recreate", "runs", "001-demo", "candidates.json"),
                       [{"name": "LatestRunCandidate",
                         "target_domain": "demo",
                         "single_question": "Is the latest run candidate loaded?"}])
            write_json(os.path.join(d, ".recreate", "runs", "001-demo", "status.json"),
                       {"run_id": "001-demo", "phase": "implemented",
                        "winner": "LatestRunCandidate"})

            state = load_exploit_state(d)

        self.assertEqual(state["registry"]["schema_version"], "1.0")
        self.assertEqual(state["candidates"][0]["name"], "LatestRunCandidate")
        self.assertEqual(state["run_status"]["phase"], "implemented")

    def test_fixture_style_root_still_loads_flat_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            write_json(os.path.join(d, "candidates.json"),
                       [{"name": "FlatCandidate", "target_domain": "demo"}])

            state = load_exploit_state(d)

        self.assertEqual(state["candidates"][0]["name"], "FlatCandidate")
        self.assertIsNone(state["run_status"])


if __name__ == "__main__":
    unittest.main()
