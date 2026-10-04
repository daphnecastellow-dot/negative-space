import tempfile
import unittest
from pathlib import Path
from negative_space import NegativeSpaceError, add_check, add_hypothesis, change_status, dead_ends, load, new_project, render_markdown, render_mermaid, save

class NegativeSpaceTests(unittest.TestCase):
    def test_not_found_does_not_auto_reject(self):
        data = new_project("Test")
        hid = add_hypothesis(data, "A diary entry exists.")
        add_check(data, hid, "1904 diary", "manual page-by-page review", "Entry describing the bell", "not-found", "No matching entry was found in the reviewed pages.")
        self.assertEqual(data["hypotheses"][0]["status"], "open")

    def test_status_change_requires_reason_and_preserves_history(self):
        data = new_project("Test")
        hid = add_hypothesis(data, "Weather caused the event.")
        with self.assertRaises(NegativeSpaceError):
            change_status(data, hid, "parked", "")
        change_status(data, hid, "parked", "Available weather records are inconclusive.", "Reopen if station logs are found.")
        h = data["hypotheses"][0]
        self.assertEqual(h["status"], "parked")
        self.assertEqual(h["history"][-1]["previous_status"], "open")
        self.assertIn("station logs", h["reopen_when"])

    def test_round_trip_and_renderers(self):
        data = new_project("Render")
        hid = add_hypothesis(data, "A warning note was left.")
        add_check(data, hid, "Archive scan", "catalog search", "warning note", "not-found", "No note located.")
        change_status(data, hid, "weakened", "The archive search did not locate the expected note.")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "negative.json"; save(p, data); loaded = load(p)
        self.assertIn("not-found", render_markdown(loaded))
        self.assertIn("checked by", render_mermaid(loaded))

    def test_dead_end_report(self):
        data = new_project("Dead end")
        hid = add_hypothesis(data, "The story came from a 1960 pamphlet.")
        add_check(data, hid, "Pamphlet catalogs", "catalog search", "matching title", "not-found", "No matching pamphlet located.")
        change_status(data, hid, "rejected", "The cited pamphlet appears to be a miscitation.", "Reopen if a physical copy or catalog record appears.")
        report = dead_ends(data)
        self.assertIn("rejected", report)
        self.assertIn("Reopen when", report)

if __name__ == "__main__": unittest.main()
