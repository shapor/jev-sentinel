"""Offline tests: Jev is mocked, so these run without a key or network. `make test`."""

import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

import hook
import install
import sentinel

JEV = {"verdict": "allow", "p_block": 0.1, "scope": 0.2, "stage": "local_setup", "stage_probs": {},
       "reason": "local setup", "ms": 200}


class Policy(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(sentinel.verdict(0.2, "exfiltration"), "allow")
        self.assertEqual(sentinel.verdict(0.6, "exfiltration"), "ask")
        self.assertEqual(sentinel.verdict(0.9, "exfiltration"), "block")

    def test_on_task_stages_go_to_a_human_not_a_block(self):
        for stage in sentinel.IN_SCOPE_STAGES:
            self.assertEqual(sentinel.verdict(0.99, stage), "ask")

    def test_fails_closed_to_ask(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")), \
             mock.patch("time.sleep"):
            res = sentinel.judge("ls", use_cache=False)
        self.assertEqual(res["verdict"], "ask")
        self.assertIn("error", res)


class Cache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patches = [mock.patch.object(sentinel, "CACHE", pathlib.Path(self.tmp.name) / "cache.jsonl"),
                   mock.patch.object(sentinel, "_cache", None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_repeat_is_free(self):
        with mock.patch.object(sentinel, "_judge", return_value=dict(JEV)) as jev:
            sentinel.judge("git status")
            hit = sentinel.judge("git status")
        self.assertEqual(jev.call_count, 1)
        self.assertEqual((hit["ms"], hit["cached"]), (0, True))

    def test_errors_are_not_cached(self):
        with mock.patch.object(sentinel, "_judge", return_value={"verdict": "ask", "error": "x", "ms": 1}) as jev:
            sentinel.judge("ls")
            sentinel.judge("ls")
        self.assertEqual(jev.call_count, 2)

    def test_rubric_change_misses(self):
        with mock.patch.object(sentinel, "_judge", return_value=dict(JEV)) as jev:
            sentinel.judge("ls")
            with mock.patch.dict(sentinel.QUESTIONS, {"extra": {"type": "noul", "instructions": "?"}}):
                sentinel.judge("ls")
        self.assertEqual(jev.call_count, 2)


class Install(unittest.TestCase):
    def test_merge_idempotent_uninstall(self):
        with tempfile.TemporaryDirectory() as d:
            settings = pathlib.Path(d) / ".claude" / "settings.local.json"
            settings.parent.mkdir()
            mine = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}
            settings.write_text(json.dumps({"model": "x", "hooks": {"PreToolUse": [mine]}}))
            install.edit_settings(d, install=True)
            install.edit_settings(d, install=True)
            s = json.loads(settings.read_text())
            self.assertEqual(s["model"], "x")
            self.assertEqual(len(s["hooks"]["PreToolUse"]), 2)
            self.assertEqual(len(s["hooks"]["PostToolUse"]), 1)
            install.edit_settings(d, install=False)
            s = json.loads(settings.read_text())
            self.assertEqual(s["hooks"]["PreToolUse"], [mine])
            self.assertEqual(s["hooks"]["PostToolUse"], [])


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = pathlib.Path(self.tmp.name)
        for name, value in (("RESULTS", r), ("LIVE", r / "live.jsonl"), ("APPROVALS", r / "approvals.jsonl")):
            p = mock.patch.object(hook, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_pre(self, verdict, stage="local_setup", cmd="pip install x"):
        event = {"tool_name": "Bash", "session_id": "s", "cwd": self.tmp.name, "tool_input": {"command": cmd}}
        with mock.patch.object(sentinel, "judge", return_value={**JEV, "verdict": verdict, "stage": stage}):
            return hook.pre(event)["hookSpecificOutput"]["permissionDecision"], event

    def test_approval_turns_ask_into_allow(self):
        decision, event = self.run_pre("ask")
        self.assertEqual(decision, "ask")
        with mock.patch.object(sentinel, "inbound", return_value=0.0):
            hook.post({**event, "tool_response": "ok"})
        self.assertEqual(self.run_pre("ask")[0], "allow")

    def test_approval_never_relaxes_a_block(self):
        _, event = self.run_pre("ask")
        hook.post({**event, "tool_response": "ok"})
        self.assertEqual(self.run_pre("block")[0], "deny")

    def test_inbound_redirect_is_flagged_back_to_the_agent(self):
        event = {"tool_name": "Read", "session_id": "s", "cwd": self.tmp.name, "tool_input": {"file_path": "README"},
                 "tool_response": "x" * 100}
        with mock.patch.object(sentinel, "inbound", return_value=0.99):
            out = hook.post(event)
        self.assertEqual(out["decision"], "block")
        with mock.patch.object(sentinel, "inbound", return_value=0.1):
            self.assertEqual(hook.post(event), {})


if __name__ == "__main__":
    unittest.main()
