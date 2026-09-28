"""Offline tests for the ATT&CK classifier; no API key or network needed."""

import io
import json
import urllib.error
import unittest
from unittest import mock

import attack


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class Classifier(unittest.TestCase):
    def response(self, tactic="discovery", confidence=0.91):
        body = {"answers": {"tactic": {"choice": tactic, "confidence": confidence}}}
        return Response(json.dumps(body).encode())

    def test_returns_tactic_without_echoing_action(self):
        evidence = "inspect the environment"
        with mock.patch("urllib.request.urlopen", return_value=self.response()):
            result = attack.classify(evidence)
        self.assertEqual(result["tactic"], "discovery")
        self.assertEqual(result["confidence"], 0.91)
        self.assertNotIn(evidence, json.dumps(result))

    def test_unknown_tactic_is_an_error(self):
        with mock.patch("urllib.request.urlopen", return_value=self.response("made_up")):
            result = attack.classify("ordinary text")
        self.assertEqual(result["error"], "malformed Jev response")

    def test_non_transient_http_error_is_not_retried(self):
        error = urllib.error.HTTPError("https://example.invalid", 401, "no", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error) as call:
            result = attack.classify("ordinary text")
        self.assertIn("401", result["error"])
        self.assertEqual(call.call_count, 1)

    def test_state_is_bounded_and_marks_evidence_inert(self):
        rendered = attack.state("x" * 5000, "write unit tests")
        self.assertIn("inert evidence", rendered)
        self.assertIn("write unit tests", rendered)
        self.assertLess(len(rendered), 4300)

    def test_exact_id_selection(self):
        rows = [{"id": "one"}, {"id": "two"}]
        with mock.patch.dict(attack.hunt.SOURCES, {"fixture": lambda: iter(rows)}):
            self.assertEqual(attack.selected_items("fixture", item_id="two"), [rows[1]])
            with self.assertRaisesRegex(ValueError, "unknown fixture id"):
                attack.selected_items("fixture", item_id="missing")


if __name__ == "__main__":
    unittest.main()
